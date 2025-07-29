from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from .models import Sale, SaleReport, ExchangeRate, Payment, Refund
from .serializers import SaleSerializer, SaleReportFilterSerializer, ExchangeRateSerializer, RefundSerializer
from products.models import Product
from stores.models import Store
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime, timedelta
from decimal import Decimal

class SaleViewSet(viewsets.ModelViewSet):
    serializer_class = SaleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        tenant = self.request.tenant
        return Sale.objects.filter(store__tenant=tenant).select_related('store')

    @action(detail=False, methods=['post'], url_path='sale')
    @transaction.atomic
    def createsale(self, request):
        tenant = request.tenant
        store_id = request.data.get('store_id')
        products_data = request.data.get('products')
        payments_data = request.data.get('payments', [])
        sale_currency = request.data.get('currency', 'USD')
        
        if not store_id or not products_data:
            return Response({"error": "store_id and products are required."}, status=status.HTTP_400_BAD_REQUEST)
        # if not payments_data:
        #     return Response({"error": "At least one payment is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            store = Store.objects.get(id=store_id,  tenant=tenant)
        except Store.DoesNotExist:
            return Response({"error": "Store not found."}, status=status.HTTP_404_NOT_FOUND)

        cashier = request.user

        
        # Validate currency
        valid_currencies = dict(Sale.CURRENCY_CHOICES).keys()
        if sale_currency not in valid_currencies:
            return Response(
                {"error": f"Invalid currency. Must be one of {list(valid_currencies)}."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        products_with_qty = []
        try:
            for item in products_data:
                product_id = item.get('product_id')
                quantity_sold = item.get('quantity_sold')

                if not product_id or not quantity_sold:
                    raise ValueError("Each product must have 'product_id' and 'quantity_sold'.")

                product = Product.objects.get(id=product_id,  tenant=tenant)
                products_with_qty.append({'product': product, 'quantity': quantity_sold})

                  # Validate payments
            valid_methods = dict(Payment.PAYMENT_METHOD_CHOICES).keys()
            for p in payments_data:
                if p['method'] not in valid_methods:
                    raise ValueError(f"Invalid payment method: {p['method']}")

            sale = Sale.process_sale(
                store=store,
                products_with_qty=products_with_qty,
                payments=payments_data,
                cashier=cashier,
                sale_currency=sale_currency,
                tenant=tenant
            )
    
        except (Product.DoesNotExist, ValueError) as e:
            transaction.set_rollback(True)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(sale)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'], url_path='listsales')
    @transaction.atomic
    def list_sales(self, request):
        tenant = request.tenant
        sales = self.get_queryset().filter(store__tenant=tenant)
        serializer = self.get_serializer(sales, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='add-payment')
    @transaction.atomic
    def add_payment(self, request, pk=None):
        sale = self.get_object()
        payments_data = request.data.get('payments', [])

        if not payments_data:
            return Response({"error": "No payment data provided."}, status=status.HTTP_400_BAD_REQUEST)

        valid_methods = dict(Payment.PAYMENT_METHOD_CHOICES).keys()
        for p in payments_data:
            if p['method'] not in valid_methods:
                return Response({"error": f"Invalid payment method: {p['method']}"}, status=status.HTTP_400_BAD_REQUEST)

        exchange_rate = Decimal(sale.exchange_rate_used)

        # ---- Check for overpayment ----
        current_paid = Decimal(sale.amount_paid)
        additional_amount = Decimal('0')

        for p in payments_data:
            pay_amount = Decimal(str(p['amount']))
            pay_currency = p.get('currency', sale.currency)

            # Convert to sale currency for validation
            if pay_currency != sale.currency:
                if sale.currency == "USD" and pay_currency == "LRD":
                    pay_amount = pay_amount / exchange_rate
                elif sale.currency == "LRD" and pay_currency == "USD":
                    pay_amount = pay_amount * exchange_rate

            additional_amount += pay_amount

        new_total = current_paid + additional_amount
        if new_total > sale.grand_total:
            return Response(
                {"error": f"Payment exceeds the outstanding balance. Balance due: {sale.balance_due}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ---- Save payments ----
        for p in payments_data:
            Payment.objects.create(
                sale=sale,
                method=p['method'],
                amount=p['amount'],
                currency=p.get('currency', sale.currency),
                status='Completed'
            )

        serializer = self.get_serializer(sale)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='cancel')
    @transaction.atomic
    def cancel_sale_api(self, request, pk=None):
        sale = self.get_object()
        reason = request.data.get("reason", "Cancelled via API")
        sale.cancel_sale(cancelled_by=request.user, reason=reason)
        return Response({"message": "Sale cancelled and inventory restored."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='remove_items')
    @transaction.atomic
    def partial_cancel_sale_api(self, request, pk=None):
        sale = self.get_object()
        items = request.data.get("items")
        reason = request.data.get("reason", "Partial cancellation via API")

        if not items or not isinstance(items, list):
            return Response({"error": "Provide a list of items with sale_detail_id and quantity."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            sale.partial_cancel(cancelled_items=items, cancelled_by=request.user, reason=reason)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"message": "Partial cancellation processed successfully."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='download-sales-report')
    def download_sales_report(self, request):
        tenant = request.tenant
        """
        Download lot sales report as PDF.
        Query params:
            - type: store/general
            - range: today/7days/30days/custom
            - start_date, end_date: used only if range=custom (YYYY-MM-DD)
        """
        report_type = request.GET.get('type', 'general')
        date_range = request.GET.get('range', '30days')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        # Handle ranges
        now = datetime.now()
        if date_range == 'today':
            start_date = end_date = now
        elif date_range == '7days':
            start_date, end_date = now - timedelta(days=7), now
        elif date_range == '30days':
            start_date, end_date = now - timedelta(days=30), now
        elif date_range == 'custom':
            if not start_date or not end_date:
                return Response({"error": "start_date and end_date are required for custom range."}, status=400)
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
            end_date = datetime.strptime(end_date, "%Y-%m-%d")
        else:
            return Response({"error": "Invalid range. Use today, 7days, 30days, or custom."}, status=400)

        # Get report data
        data = SaleReport.get_lot_sales_report(report_type, start_date, end_date,  tenant=tenant)
        if not data:
            return Response({"error": "No data found for the given filters."}, status=status.HTTP_404_NOT_FOUND)

        # Create PDF
        response = HttpResponse(content_type='application/pdf')
        filename = f"sales_report_{report_type}_{start_date.date()}_{end_date.date()}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        doc = SimpleDocTemplate(response, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []

        # Title
        elements.append(Paragraph(f"Sales Report ({report_type.capitalize()})", styles['Title']))
        elements.append(Paragraph(f"Period: {start_date.date()} - {end_date.date()}", styles['Normal']))
        elements.append(Spacer(1, 12))

        # Convert data to table format
        headers = list(data[0].keys())
        rows = [headers] + [list(row.values()) for row in data]

        table = Table(rows)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4F81BD")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(table)

        doc.build(elements)
        return response

    @action(detail=False, methods=['get'], url_path='lot-sales-report')
    @transaction.atomic
    def lot_sales_report(self, request):
        tenant = request.tenant
        serializer = SaleReportFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        report = SaleReport.get_lot_sales_report(
            start_date=data['start_date'],
            end_date=data['end_date'],
            currency=data.get('currency', 'USD'),
            cashier_id=data.get('cashier_id'),
            report_type='store', # or 'general' 
            tenant=tenant
        )
        return Response(report)
    
    
# class ExchangeRateViewSet(viewsets.ModelViewSet):
#     serializer_class = ExchangeRateSerializer
#     permission_classes = [IsAuthenticated]

#     def get_queryset(self):
#         tenant = self.request.tenant
#         return ExchangeRate.objects.filter(tenant=tenant).order_by('-effective_date')
    
#     @action(detail=False, methods=['post'], url_path='add-rate')
#     @transaction.atomic
#     def add_rate(self, request):
#         tenant = request.tenant
        
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         instance = serializer.save(tenant=tenant)
        
#         return Response(self.get_serializer(instance).data, status=status.HTTP_201_CREATED)


class ExchangeRateViewSet(viewsets.ModelViewSet):
    queryset = ExchangeRate.objects.none()  # avoids DRF errors
    serializer_class = ExchangeRateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tenant = self.request.tenant
        return ExchangeRate.objects.filter(tenant=tenant).order_by('-effective_date')
    
    @action(detail=False, methods=['post'], url_path='add-rate')
    @transaction.atomic
    def add_rate(self, request):
        tenant = request.tenant
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(tenant=tenant)
        return Response(self.get_serializer(instance).data, status=status.HTTP_201_CREATED)
    
class RefundViewSet(viewsets.ModelViewSet):
    serializer_class = RefundSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tenant = self.request.tenant
        return Refund.objects.filter(sale__store__tenant=tenant).select_related('processed_by').order_by('-processed_at')

    @transaction.atomic
    def perform_create(self, serializer):
        tenant = self.request.tenant
        serializer.save(processed_by=self.request.user, tenant=tenant)

    @action(detail=False, methods=['post'], url_path='issue-refund')
    @transaction.atomic
    def issue_refund(self, request):
        sale_id = request.data.get('sale_id')
        amount = request.data.get('amount')
        reason = request.data.get('reason', 'Refund issued')

        if not sale_id or not amount:
            return Response({"error": "sale_id and amount are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            sale = Sale.objects.get(id=sale_id, store__tenant=request.tenant)
        except Sale.DoesNotExist:
            return Response({"error": "Sale not found."}, status=status.HTTP_404_NOT_FOUND)

        refund = Refund.objects.create(
            sale=sale,
            amount=amount,
            processed_by=request.user,
            reason=reason,
            tenant=request.tenant
        )
        serializer = self.get_serializer(refund)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
