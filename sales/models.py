from django.db import models, transaction
from collections import defaultdict
from stores.models import Store
from products.models import Product, Lot
from inventory.models import Inventory, Warehouse
from django.utils import timezone
from django.db.models import Sum, F, DecimalField, ExpressionWrapper, Case, When
from customers.models import User, Client

class Sale(models.Model):
    tenant = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="sales")
    store = models.ForeignKey(Store, related_name='sales', on_delete=models.CASCADE)
    sale_date = models.DateTimeField(default=timezone.now)

    # Line totals per currency (unconverted)
    total_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_lrd = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Grand total converted into the sale currency
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    cashier = models.ForeignKey(User, related_name='sales', on_delete=models.SET_NULL, null=True, blank=True)
    receipt_number = models.CharField(max_length=20, unique=True, editable=False, null=True)

    CURRENCY_CHOICES = [('USD', 'USD'), ('LRD', 'LRD')]
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='USD')  # Sale-level currency

    PAYMENT_METHOD_CHOICES = [
        ('Cash', 'Cash'),
        ('Orange_Money', 'Orange Money'),
        ('Mobile_Money', 'Mobile Money'),
        ('Visa_MasterCard', 'Visa/MasterCard'),
    ]
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='Cash')

    # The exchange rate at the time of the sale
    exchange_rate_used = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, editable=False)

    class Meta:
        unique_together = ('tenant', 'store', 'receipt_number')  # Strict uniqueness per tenant & store

    def save(self, *args, **kwargs):
        if self.pk:
            old_receipt = Sale.objects.filter(pk=self.pk).values_list('receipt_number', flat=True).first()
            if old_receipt and self.receipt_number != old_receipt:
                raise ValueError("Editing receipt_number is not allowed.")

        if not self.exchange_rate_used:
            latest_rate = ExchangeRate.objects.filter(tenant=self.tenant).order_by('-effective_date').first()
            if not latest_rate:
                raise ValueError("No exchange rate found for tenant.")
            self.exchange_rate_used = latest_rate.usd_rate

        # Always recompute the grand total
        if self.currency == 'USD':
            self.grand_total = self.total_usd + (self.total_lrd / self.exchange_rate_used)
        else:  # Sale in LRD
            self.grand_total = self.total_lrd + (self.total_usd * self.exchange_rate_used)

        super().save(*args, **kwargs)

    @staticmethod
    def generate_receipt_number(tenant, store):
        today = timezone.now().date()
        current_year = today.year
        with transaction.atomic():
            last_sale = (
                Sale.objects.select_for_update()
                .filter(
                    tenant=tenant,
                    store=store,
                    sale_date__year=current_year
                )
                .order_by('-id')
                .first()
            )
            prefix = chr(64 + store.id)  # Store-specific prefix
            last_number = 0
            if last_sale and last_sale.receipt_number:
                try:
                    last_number = int(last_sale.receipt_number.split('-')[-1])
                except ValueError:
                    last_number = 0
            new_number = last_number + 1
            return f"T{tenant.id}S{prefix}{current_year}-{new_number:04d}"  # Example: T1SA2025-0001
        
    def __str__(self):
        return f"{self.receipt_number} - {self.store.store_name} ({self.currency})"
    
    @staticmethod
    @transaction.atomic
    def process_sale(tenant, store, products_with_qty, cashier=None, payment_method=None, sale_currency='USD'):
        if store.tenant_id != tenant.id:
            raise ValueError("Store does not belong to this tenant.")

        try:
            warehouse = store.warehouses.get(warehouse_type='store', tenant=tenant)
        except Warehouse.DoesNotExist:
            raise ValueError(f"No warehouse found for store {store.store_name}.")

        receipt_number = Sale.generate_receipt_number(tenant, store)
        latest_rate = ExchangeRate.objects.filter(tenant=tenant).order_by('-effective_date').first()
        if not latest_rate:
            raise ValueError("No exchange rate found.")
        rate = latest_rate.usd_rate

        sale = Sale.objects.create(
            tenant=tenant,
            store=store,
            sale_date=timezone.now(),
            cashier=cashier,
            payment_method=payment_method,
            receipt_number=receipt_number,
            currency=sale_currency,
            exchange_rate_used=rate,
        )

        total_usd = 0
        total_lrd = 0

        for item in products_with_qty:
            product = item['product'] 
            if product.tenant_id != tenant.id:
                raise ValueError(f"Product {product.product_name} does not belong to this tenant.")
            quantity_sold = item['quantity']
            product_currency = product.currency
            price = product.retail_price

            store_inventory = Inventory.objects.filter(
                warehouse=warehouse,
                product=product,
                quantity__gt=0,
                tenant=tenant
            ).select_related('lot').order_by('lot__purchase_date')

            quantity_left = quantity_sold
            lots_used = []
            total_available = sum(inv.quantity for inv in store_inventory)
            if total_available < quantity_sold:
                raise ValueError(f"Insufficient stock for {product.product_name}. Requested {quantity_sold}, available {total_available}.")

            for inventory in store_inventory:
                if quantity_left <= 0:
                    break
                if inventory.lot.expired_date and inventory.lot.expired_date < timezone.now().date():
                    continue
                deduct_qty = min(inventory.quantity, quantity_left)
                lots_used.append((inventory.lot, deduct_qty))
                inventory.deduct_quantity(deduct_qty)
                quantity_left -= deduct_qty

            if quantity_left > 0:
                raise ValueError(f"Unexpected stock mismatch for {product.product_name}.")

            # from .models import SaleDetail
            for lot, qty in lots_used:
                line_total = qty * price
                SaleDetail.objects.create(
                    tenant=tenant,
                    sale=sale,
                    product=product,
                    lot=lot,
                    quantity_sold=qty,
                    price_at_sale=price,
                    currency=product_currency
                )
                if product_currency == 'USD':
                    total_usd += line_total
                else:
                    total_lrd += line_total

        sale.total_usd = total_usd
        sale.total_lrd = total_lrd
        # Grand total will be computed in save()
        sale.save()
        return sale

    def get_total_in_usd(self):
        """
        Returns the grand total of this sale expressed in USD,
        converting LRD total using the stored exchange rate.
        """
        if self.currency == 'USD':
            # Already in USD, just sum totals
            return self.total_usd + (self.total_lrd / self.exchange_rate_used if self.exchange_rate_used else 0)
        else:
            # Sale is in LRD, so total_usd is raw USD lines, total_lrd is sale currency, convert LRD to USD
            return self.total_usd + (self.total_lrd / self.exchange_rate_used if self.exchange_rate_used else 0)

    def get_total_in_lrd(self):
        """
        Returns the grand total of this sale expressed in LRD,
        converting USD total using the stored exchange rate.
        """
        if self.currency == 'LRD':
            # Already in LRD
            return self.total_lrd + (self.total_usd * self.exchange_rate_used if self.exchange_rate_used else 0)
        else:
            # Sale is in USD, so total_lrd is raw LRD lines, total_usd is sale currency, convert USD to LRD
            return self.total_lrd + (self.total_usd * self.exchange_rate_used if self.exchange_rate_used else 0)
        
    def __str__(self):
        return f"{self.receipt_number} - {self.store.store_name} on {self.sale_date} ({self.currency})"

class SaleDetail(models.Model):
    sale = models.ForeignKey(Sale, related_name="sale_details", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    lot = models.ForeignKey(Lot, null=True, blank=True, on_delete=models.CASCADE)
    quantity_sold = models.IntegerField()
    price_at_sale = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, choices=[('USD', 'USD'), ('LRD', 'LRD')], default='LRD')  # from product
    
    def __str__(self):
        return f"{self.product.name} - Lot {self.lot.id} - {self.quantity_sold} units in sale {self.sale.id}"

class ExchangeRate(models.Model):
    tenant = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="exchange_rates")
    usd_rate = models.DecimalField(max_digits=10, decimal_places=2)
    effective_date = models.DateField(editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('tenant', 'effective_date')
        ordering = ['-effective_date']

    def save(self, *args, **kwargs):
        if not self.pk:  # Only set on creation
            self.effective_date = timezone.now().date()
        super().save(*args, **kwargs)

    def __str__(self):
        return f" {self.tenant.name} USD Rate: {self.usd_rate} (Effective: {self.effective_date})"

class SaleReport:
    @staticmethod
    def get_lot_sales_report(tenant, report_type='general', start_date=None, end_date=None, currency='USD',
                             cashier_id=None, payment_method=None):
        filters = {'sale__tenant': tenant}  # <-- Enforce tenant filtering
        if start_date and end_date:
            filters['sale__sale_date__range'] = (start_date, end_date)
        if cashier_id:
            filters['sale__cashier__id'] = cashier_id
        if payment_method:
            filters['sale__payment_method'] = payment_method

        usd_revenue_expr = ExpressionWrapper(
            Case(
                When(currency='USD', then=F('quantity_sold') * F('price_at_sale')),
                default=0,
                output_field=DecimalField(max_digits=12, decimal_places=2)
            ), output_field=DecimalField(max_digits=12, decimal_places=2)
        )
        lrd_revenue_expr = ExpressionWrapper(
            Case(
                When(currency='LRD', then=F('quantity_sold') * F('price_at_sale')),
                default=0,
                output_field=DecimalField(max_digits=12, decimal_places=2)
            ), output_field=DecimalField(max_digits=12, decimal_places=2)
        )
        if currency == 'USD':
            converted_revenue_expr = ExpressionWrapper(
                Case(
                    When(currency='USD', then=F('quantity_sold') * F('price_at_sale')),
                    When(currency='LRD', then=(F('quantity_sold') * F('price_at_sale')) / F('sale__exchange_rate_used')),
                    default=0,
                    output_field=DecimalField(max_digits=12, decimal_places=2)
                ), output_field=DecimalField(max_digits=12, decimal_places=2)
            )
        else:
            converted_revenue_expr = ExpressionWrapper(
                Case(
                    When(currency='LRD', then=F('quantity_sold') * F('price_at_sale')),
                    When(currency='USD', then=(F('quantity_sold') * F('price_at_sale')) * F('sale__exchange_rate_used')),
                    default=0,
                    output_field=DecimalField(max_digits=12, decimal_places=2)
                ), output_field=DecimalField(max_digits=12, decimal_places=2)
            )

        qs = (SaleDetail.objects
                .filter(**filters)
                .annotate(
                    usd_revenue=usd_revenue_expr,
                    lrd_revenue=lrd_revenue_expr,
                    converted_revenue=converted_revenue_expr,
                    exchange_rate=F('sale__exchange_rate_used')
                ))

        if report_type == 'store':
            qs = qs.values(
                'sale__store__store_name',
                'product__product_name',
                'lot__sku',
                'lot__expired_date',
                'exchange_rate'
            ).annotate(
                total_quantity=Sum('quantity_sold'),
                total_usd_revenue=Sum('usd_revenue'),
                total_lrd_revenue=Sum('lrd_revenue'),
                total_converted_revenue=Sum('converted_revenue')
            ).order_by('sale__store__store_name', 'product__product_name')
        else:
            qs = qs.values(
                'product__product_name',
                'lot__sku',
                'lot__expired_date',
                'exchange_rate'
            ).annotate(
                total_quantity=Sum('quantity_sold'),
                total_usd_revenue=Sum('usd_revenue'),
                total_lrd_revenue=Sum('lrd_revenue'),
                total_converted_revenue=Sum('converted_revenue')
            ).order_by('product__product_name')

        report_data = list(qs)

        sale_filters = {'tenant': tenant}  # <-- Tenant enforced
        if start_date and end_date:
            sale_filters['sale_date__range'] = (start_date, end_date)
        if cashier_id:
            sale_filters['cashier__id'] = cashier_id
        if payment_method:
            sale_filters['payment_method'] = payment_method

        sales = Sale.objects.filter(**sale_filters).select_related('store', 'cashier')

        total_in_usd = sum(s.get_total_in_usd() for s in sales)
        total_in_lrd = sum(s.get_total_in_lrd() for s in sales)
        grand_total = total_in_usd if currency == 'USD' else total_in_lrd

        detailed_sales_by_date = defaultdict(list)
        for s in sales:
            converted_total = s.get_total_in_usd() if currency == 'USD' else s.get_total_in_lrd()
            detailed_sales_by_date[s.sale_date.date()].append({
                "receipt_number": s.receipt_number,
                "payment_method": s.payment_method,
                "currency": s.currency,
                "cashier_id": s.cashier.id if s.cashier else None,
                "total_usd": s.total_usd,
                "total_lrd": s.total_lrd,
                "converted_total": converted_total,
                "exchange_rate": s.exchange_rate_used,
                "store": s.store.store_name,
            })

        detailed_sales = [
            {"date": date, "sales": sales}
            for date, sales in sorted(detailed_sales_by_date.items())
        ]

        daily_totals = defaultdict(lambda: {'usd': 0, 'lrd': 0, 'converted': 0})
        for s in sales:
            date_key = s.sale_date.date()
            daily_totals[date_key]['usd'] += s.total_usd
            daily_totals[date_key]['lrd'] += s.total_lrd
            daily_totals[date_key]['converted'] += s.get_total_in_usd() if currency == 'USD' else s.get_total_in_lrd()

        daily_breakdown = [{'date': date, **totals} for date, totals in sorted(daily_totals.items())]

        daily_store_totals = defaultdict(lambda: defaultdict(lambda: {'usd': 0, 'lrd': 0, 'converted': 0}))
        for s in sales:
            date_key = s.sale_date.date()
            store_name = s.store.store_name
            daily_store_totals[date_key][store_name]['usd'] += s.total_usd
            daily_store_totals[date_key][store_name]['lrd'] += s.total_lrd
            daily_store_totals[date_key][store_name]['converted'] += s.get_total_in_usd() if currency == 'USD' else s.get_total_in_lrd()

        daily_store_breakdown = [
            {'date': date, 'stores': [{'store': store, **totals} for store, totals in store_data.items()]}
            for date, store_data in sorted(daily_store_totals.items())
        ]

        store_totals = defaultdict(lambda: {'store_total_usd': 0, 'store_total_lrd': 0, 'store_total_converted': 0})
        for s in sales:
            store_name = s.store.store_name
            store_totals[store_name]['store_total_usd'] += s.total_usd
            store_totals[store_name]['store_total_lrd'] += s.total_lrd
            store_totals[store_name]['store_total_converted'] += s.get_total_in_usd() if currency == 'USD' else s.get_total_in_lrd()

        store_breakdown = [{"store__store_name": name, **totals} for name, totals in store_totals.items()]

        currency_breakdown = {'total_usd': total_in_usd, 'total_lrd': total_in_lrd}

        return {
            "report_data": report_data,
            "detailed_sales": detailed_sales,
            "grand_total_usd": total_in_usd,
            "grand_total_lrd": total_in_lrd,
            "grand_total_in_selected_currency": grand_total,
            "daily_breakdown": daily_breakdown,
            "daily_store_breakdown": daily_store_breakdown,
            "store_breakdown": store_breakdown,
            "currency_breakdown": currency_breakdown
        }


#How sales report will look 
# [
#     {
#         'sale__id': 101,
#         'sale__sale_date': datetime.date(2025,7,22),
#         'sale__store__store_name': 'Downtown Store',
#         'product__name': 'Product A',
#         'lot__id': 5,
#         'lot__batch_number': 'BATCH-123',
#         'lot__expiry_date': datetime.date(2025,12,31),
#         'total_quantity': 10
#     },
#     {
#         'sale__id': 102,
#         'sale__sale_date': datetime.date(2025,7,23),
#         'sale__store__store_name': 'Mall Outlet',
#         'product__name': 'Product A',
#         'lot__id': 6,
#         'lot__batch_number': 'BATCH-124',
#         'lot__expiry_date': datetime.date(2026,1,15),
#         'total_quantity': 15
#     }
# ]



# class Order(models.Model):
#     customer = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="orders")
#     created_at = models.DateTimeField(auto_now_add=True)
#     status = models.CharField(
#         max_length=20,
#         choices=[("Pending", "Pending"), ("Completed", "Completed"), ("Cancelled", "Cancelled")],
#         default="Pending",
#     )

#     def __str__(self):
#         return f"Order {self.id} - {self.customer}"

# class OrderItem(models.Model):
#     order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
#     product = models.ForeignKey(Product, on_delete=models.CASCADE)
#     quantity = models.PositiveIntegerField()

#     def __str__(self):
#         return f"{self.quantity} x {self.product.product_name} (Order {self.order.id})"

#     def save(self, *args, **kwargs):
#         """Auto-deduct stock from available lots when an order is placed."""
#         if not self.pk:  # Only deduct stock on the first save (avoid double deduction)
#             self.deduct_stock()
#         super().save(*args, **kwargs)

#     def deduct_stock(self):
#         """Deduct stock from the oldest available lots (FIFO system)."""
#         remaining_qty = self.quantity
#         available_lots = (
#             self.product.lots.filter(quantity__gt=0, expired_date__gte=timezone.now()).order_by("purchase_date")
#         )

#         for lot in available_lots:
#             if remaining_qty <= 0:
#                 break

#             if lot.quantity >= remaining_qty:
#                 lot.quantity -= remaining_qty
#                 remaining_qty = 0
#             else:
#                 remaining_qty -= lot.quantity
#                 lot.quantity = 0

#             lot.save()  # Save the updated lot quantity

#         if remaining_qty > 0:
#             raise ValueError(f"Not enough stock available for {self.product.product_name}. Order cannot be completed.")

# def delete(self, *args, **kwargs):
#     """Restore stock to lots when an order item is deleted (order canceled)."""
#     returned_qty = self.quantity
#     used_lots = self.product.lots.filter(quantity__lt=F("initial_quantity")).order_by("-purchase_date")

#     for lot in used_lots:
#         if returned_qty <= 0:
#             break

#         space_left = lot.initial_quantity - lot.quantity
#         if space_left >= returned_qty:
#             lot.quantity += returned_qty
#             returned_qty = 0
#         else:
#             returned_qty -= space_left
#             lot.quantity = lot.initial_quantity

#         lot.save()

#     super().delete(*args, **kwargs)

