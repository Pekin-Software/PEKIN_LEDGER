from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.utils import timezone
from django.db.models.functions import Coalesce
from .models import Sale, SaleReport, ExchangeRate, Payment, Refund, SaleDetail, DashboardMonthlyStat
from .serializers import SaleSerializer, SaleReportFilterSerializer, ExchangeRateSerializer, RefundSerializer
from products.models import Product,ProductVariant, Category, ProductLot
from stores.models import Store
from inventory.models import Inventory
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime, timedelta,date
from decimal import Decimal
from calendar import month_name
from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError
import calendar
from django.db.models import Subquery, OuterRef, Sum, F, Q, Max, DecimalField, ExpressionWrapper, Value, Case, When
from inventory.services.sales_posting import (
    SalesPostingService
)

year = timezone.now().year

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
                variant_id = item.get('variant_id')
                quantity_sold = item.get('quantity_sold')

                if not product_id or not quantity_sold:
                    raise ValueError("Each product must have 'product_id' and 'quantity_sold'.")

                product = Product.objects.get(id=product_id,  tenant=tenant)

                variant = None
                if variant_id:
                    variant = ProductVariant.objects.get( id=variant_id, product=product)

                products_with_qty.append({'product': product, 'variant': variant, 'quantity': quantity_sold})

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
        return Response({
        "success": True,
        "sale": serializer.data
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="finalize")
    @transaction.atomic
    def finalize(self, request, pk=None):

        sale = self.get_object()

        SalesPostingService.post_sale(
            sale.id,
            user=request.user
        )

        sale.refresh_from_db()

        serializer = self.get_serializer(sale)

        return Response({
            "message": "Sale finalized successfully.",
            "sale": serializer.data
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], url_path='listsales')
    def list_sales(self, request):
        tenant = request.tenant
        today = timezone.now().date()
        store_id = request.query_params.get('store_id')

        # Base filter for store if provided
        store_filter = {'sale__store_id': store_id} if store_id else {}
        inventory_filter = {'warehouse__store_id': store_id} if store_id else {}
        # =====================================================
        # TOP SELLING PRODUCTS (TOP 20)
        # =====================================================
        last_sale_date_subquery = Subquery(
            SaleDetail.objects
            .filter(
                product=OuterRef('product'),
                sale__tenant=tenant,
                sale__payment_status='Completed',
                sale__sale_date__lt=today,
                **store_filter
            )
            .order_by('-sale__sale_date')
            .values('sale__sale_date')[:1]
        )

        inventory = (
            Inventory.objects.filter(tenant=tenant, **inventory_filter)
            .values('product')
            .annotate(
                product_name=F('product__product_name'),
                product_image=F('product__product_image'),
                category=F('product__category__name'),
                remaining_qty=Coalesce(
                    Subquery(
                        Inventory.objects.filter(
                            tenant=tenant,
                            product=OuterRef('product'),
                            **inventory_filter
                        )
                        .values('product')
                        .annotate(total_qty=Coalesce(Sum('quantity'), 0))
                        .values('total_qty')[:1]
                    ),
                    Value(Decimal('0.00')),
                    output_field=DecimalField(max_digits=14, decimal_places=2)
                ),
                price=Max('lot__retail_selling_price'),

                # Today's revenue
                today_revenue=Coalesce(
                    Sum(
                        ExpressionWrapper(
                            F('product__saledetail__quantity_sold') *
                            F('product__saledetail__price_at_sale'),
                            output_field=DecimalField(max_digits=14, decimal_places=2)
                        ),
                        filter=Q(
                            product__saledetail__sale__tenant=tenant,
                            product__saledetail__sale__payment_status='Completed',
                            product__saledetail__sale__sale_date__date=today,
                            **({'product__saledetail__sale__store_id': store_id} if store_id else {})
                        )
                    ),
                    Value(Decimal('0.00')),
                    output_field=DecimalField(max_digits=14, decimal_places=2)
                ),

                last_sale_date=last_sale_date_subquery
            )
        )

        previous_revenue_subquery = Subquery(
            SaleDetail.objects
            .filter(
                product=OuterRef('product'),
                sale__tenant=tenant,
                sale__payment_status='Completed',
                sale__sale_date=OuterRef('last_sale_date'),
                **({'sale__store_id': store_id} if store_id else {})
            )
            .annotate(
                revenue=ExpressionWrapper(
                    F('quantity_sold') * F('price_at_sale'),
                    output_field=DecimalField(max_digits=14, decimal_places=2)
                )
            )
            .values('product')
            .annotate(total=Sum('revenue'))
            .values('total')
        )

        inventory = inventory.annotate(
            previous_revenue=Coalesce(
                previous_revenue_subquery,
                Value(Decimal('0.00')),
                output_field=DecimalField(max_digits=14, decimal_places=2)
            )
        ).annotate(
            increase_by=ExpressionWrapper(
                Case(
                    When(previous_revenue__gt=0,
                        then=((F('today_revenue') - F('previous_revenue')) / F('previous_revenue'))),
                    default=Value(Decimal('100.0')),
                ),
                output_field=DecimalField(max_digits=7, decimal_places=2)
            )
        ).order_by('-today_revenue', '-previous_revenue')[:20]

        # =====================================================
        # BEST SELLING CATEGORY (TOP 3)
        # =====================================================
        last_category_sale_date = Subquery(
            SaleDetail.objects
            .filter(
                product__category=OuterRef('pk'),
                sale__tenant=tenant,
                sale__payment_status='Completed',
                sale__sale_date__lt=today,
                **({'sale__store_id': store_id} if store_id else {})
            )
            .order_by('-sale__sale_date')
            .values('sale__sale_date')[:1]
        )

        categories = Category.objects.annotate(
            today_turnover=Coalesce(
                Sum(
                    ExpressionWrapper(
                        F('products__saledetail__quantity_sold') *
                        F('products__saledetail__price_at_sale'),
                        output_field=DecimalField(max_digits=14, decimal_places=2)
                    ),
                    filter=Q(
                        products__saledetail__sale__tenant=tenant,
                        products__saledetail__sale__payment_status='Completed',
                        products__saledetail__sale__sale_date__date=today,
                        **({'products__saledetail__sale__store_id': store_id} if store_id else {})
                    )
                ),
                Value(Decimal('0.00')),
                output_field=DecimalField(max_digits=14, decimal_places=2)
            ),
            last_sale_date=last_category_sale_date
        )

        previous_category_revenue = Subquery(
            SaleDetail.objects
            .filter(
                product__category=OuterRef('pk'),
                sale__tenant=tenant,
                sale__payment_status='Completed',
                sale__sale_date=OuterRef('last_sale_date'),
                **({'sale__store_id': store_id} if store_id else {})
            )
            .annotate(
                revenue=ExpressionWrapper(
                    F('quantity_sold') * F('price_at_sale'),
                    output_field=DecimalField(max_digits=14, decimal_places=2)
                )
            )
            .values('product__category')
            .annotate(total=Sum('revenue'))
            .values('total')
        )

        categories = categories.annotate(
            previous_turnover=Coalesce(
                previous_category_revenue,
                Value(Decimal('0.00')),
                output_field=DecimalField(max_digits=14, decimal_places=2)
            )
        ).annotate(
            increase_by=ExpressionWrapper(
                Case(
                    When(previous_turnover__gt=0,
                        then=((F('today_turnover') - F('previous_turnover')) / F('previous_turnover'))),
                    default=Value(Decimal('0.00')),
                ),
                output_field=DecimalField(max_digits=7, decimal_places=2)
            )
        ).values(
            category_name=F('name'),
            turn_over=F('today_turnover'),
            increase_by=F('increase_by'),
            previous_turnover=F('previous_turnover')
        ).order_by('-turn_over', '-previous_turnover')[:3]

        # =====================================================
        # MONTHLY PROFIT & REVENUE (LAST 12 MONTHS)
        # =====================================================
        first_stat = DashboardMonthlyStat.objects.filter(tenant=tenant).order_by('year', 'month').first()
        if first_stat:
            start_date = date(first_stat.year, first_stat.month, 1)
        else:
            start_date = date(today.year, today.month, 1)

        months = [(start_date + relativedelta(months=i)).timetuple()[:2] for i in range(12)]
        stats = DashboardMonthlyStat.objects.filter(
            tenant=tenant,
            year__gte=months[0][0],
            year__lte=months[-1][0],
            month__in=[m for y, m in months]
        )
        stats_map = {(s.year, s.month): s for s in stats}

        ProfitRevenue = [
            {
                # "month": f"{month_name[m]} {y}",
                "month": f"{calendar.month_abbr[m]} {y}",
                "revenue": stats_map.get((y, m)).revenue if (y, m) in stats_map else Decimal("0.00"),
                "profit": stats_map.get((y, m)).profit if (y, m) in stats_map else Decimal("0.00"),
            }
            for y, m in months
        ]

        # =====================================================
        # BASE REPORT AGGREGATES
        # =====================================================
        base_sales = SaleDetail.objects.filter(
            sale__tenant=tenant,
            sale__payment_status='Completed',
            **({'sale__store_id': store_id} if store_id else {})
        )

        aggregates = base_sales.aggregate(
            total_sales=Coalesce(
                Sum(F('quantity_sold') * F('price_at_sale'),
                    output_field=DecimalField(max_digits=14, decimal_places=2)),
                Decimal('0.00')
            ),
            total_cogs=Coalesce(
                Sum(F('quantity_sold') * F('lot__purchase_price'),
                    output_field=DecimalField(max_digits=14, decimal_places=2)),
                Decimal('0.00')
            ),
            this_month_revenue=Coalesce(
                Sum(
                    F('quantity_sold') * F('price_at_sale'),
                    filter=Q(
                        sale__sale_date__month=today.month,
                        sale__sale_date__year=year
                    ),
                    output_field=DecimalField(max_digits=14, decimal_places=2)
                ),
                Decimal('0.00')
            ),
            last_month_revenue=Coalesce(
                Sum(
                    F('quantity_sold') * F('price_at_sale'),
                    filter=Q(
                        sale__sale_date__month=(today.month - 1 or 12),
                        sale__sale_date__year=year if today.month > 1 else year - 1
                    ),
                    output_field=DecimalField(max_digits=14, decimal_places=2)
                ),
                Decimal('0.00')
            ),
        )
        total_sales = aggregates["total_sales"]
        cogs = aggregates["total_cogs"]

        # =====================================================
        # PURCHASE COST
        # =====================================================
        purchase_cost = ProductLot.objects.filter(
            warehouse__tenant=tenant
        ).aggregate(
            total=Coalesce(
                Sum(F('purchase_price') * F('quantity'),
                    output_field=DecimalField(max_digits=14, decimal_places=2)),
                Decimal('0.00')
            )
        )["total"]

        

        mom = (
            ((aggregates["this_month_revenue"] - aggregates["last_month_revenue"])
            / aggregates["last_month_revenue"]) * 100
            if aggregates["last_month_revenue"] > 0 else Decimal("0.00")
        )

        report_overview = {
            "Purchase_cost": purchase_cost,
            "sales": total_sales,
            "net_sales": total_sales,
            "revenue": total_sales,
            "net_profit": total_sales - cogs,
            "cogs": cogs,
            "MoM": mom
        }

        return Response({
            "report_overview": report_overview,
            "ProfitRevenue": ProfitRevenue,
            "top_selling_products": inventory,
            "best_selling_category": categories
        })



        @action(detail=True, methods=['post'], url_path='add-payment')
        @transaction.atomic
        def add_payment(self, request, pk=None):
            sale = self.get_object()
            payments_data = request.data.get('payments', [])

            if sale.payment_status == 'Cancelled':
                return Response({"error": "Cannot make a payment to a cancelled sale."}, status=status.HTTP_400_BAD_REQUEST)

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
            # for p in payments_data:
            #     Payment.objects.create(
            #         sale=sale,
            #         method=p['method'],
            #         amount=p['amount'],
            #         currency=p.get('currency', sale.currency),
            #         status='Completed'
            #     )
            try:
                for p in payments_data:
                    Payment.objects.create(
                        sale=sale,
                        method=p['method'],
                        amount=p['amount'],
                        currency=p.get('currency', sale.currency),
                        status='Completed'
                    )
            except DjangoValidationError as e:
                raise DRFValidationError(e.messages)

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
           
class ExchangeRateViewSet(viewsets.ModelViewSet):
    queryset = ExchangeRate.objects.none() 
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


