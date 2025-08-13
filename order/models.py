from django.db import models, transaction
from django.utils import timezone
from decimal import Decimal
from inventory.models import Product, ProductVariant, Warehouse, Inventory, ProductLot
from sales.models import Sale, SaleDetail
from customers.models import Client, User
from stores.models import  Store
from finance.models import ExchangeRate
from django.core.exceptions import ValidationError


class Order(models.Model):
    order_number = models.CharField(max_length=20, unique=True, editable=False, null=True)
    tenant = models.ForeignKey(Client, on_delete=models.CASCADE)
    customer = models.ForeignKey(User, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, related_name='orders', on_delete=models.CASCADE)
    order_date = models.DateTimeField(default=timezone.now)

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Partially Fulfilled', 'Partially Fulfilled'),
        ('Fulfilled', 'Fulfilled'),
        ('Cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='Pending')

    currency = models.CharField(max_length=3, choices=[('USD', 'USD'), ('LRD', 'LRD')], default='USD')
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Order #{self.id} - {self.customer.customer_name} ({self.status})"

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def is_fulfilled(self):
        return all(item.quantity_fulfilled >= item.quantity for item in self.items.all())

    @transaction.atomic
    def create_sale_from_order(self, cashier=None, payments=[]):
        """
        Fulfill the full order (if possible).
        """
        if self.status in ['Fulfilled', 'Cancelled']:
            raise ValidationError("Cannot fulfill an order that is already Fulfilled or Cancelled.")

        products_with_qty = []
        for item in self.items.all():
            remaining_qty = item.remaining_quantity
            if remaining_qty <= 0:
                continue
            products_with_qty.append({
                'product': item.product,
                'variant': item.product_variant,
                'quantity': remaining_qty
            })

        sale = Sale.process_sale(
            tenant=self.tenant,
            store=self.store,
            products_with_qty=products_with_qty,
            payments=payments,
            cashier=cashier,
            sale_currency=self.currency
        )

        # Update fulfillment tracking
        for detail in sale.sale_details.all():
            item = self.items.get(product=detail.product, product_variant=detail.product_variant)
            item.quantity_fulfilled += detail.quantity_sold
            item.save()

        # Update order status
        self.status = 'Fulfilled' if self.is_fulfilled else 'Partially Fulfilled'
        self.save(update_fields=['status'])

        return sale

    @transaction.atomic
    def create_partial_sale(self, items_to_fulfill, cashier=None, payments=[]):
        """
        Fulfill only selected items (partial fulfillment).
        items_to_fulfill: List of dicts → [{'item_id': id, 'quantity': qty}, ...]
        """
        if self.status in ['Fulfilled', 'Cancelled']:
            raise ValidationError("Cannot fulfill a completed or cancelled order.")

        products_with_qty = []

        for entry in items_to_fulfill:
            try:
                item = self.items.get(pk=entry['item_id'])
            except OrderItem.DoesNotExist:
                raise ValidationError(f"Order item {entry['item_id']} not found.")

            quantity = int(entry['quantity'])
            if quantity <= 0:
                continue

            if quantity > item.remaining_quantity:
                raise ValidationError(f"Cannot fulfill more than remaining quantity for {item.product.product_name}.")

            products_with_qty.append({
                'product': item.product,
                'variant': item.product_variant,
                'quantity': quantity
            })

        if not products_with_qty:
            raise ValidationError("No valid items to fulfill.")

        sale = Sale.process_sale(
            tenant=self.tenant,
            store=self.store,
            products_with_qty=products_with_qty,
            payments=payments,
            cashier=cashier,
            sale_currency=self.currency
        )

        for detail in sale.sale_details.all():
            item = self.items.get(product=detail.product, product_variant=detail.product_variant)
            item.quantity_fulfilled += detail.quantity_sold
            item.save()

        self.status = 'Fulfilled' if self.is_fulfilled else 'Partially Fulfilled'
        self.save(update_fields=['status'])

        return sale


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    quantity_fulfilled = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('order', 'product', 'product_variant')

    def __str__(self):
        return f"{self.quantity} x {self.product.product_name} ({self.product_variant})"

    @property
    def remaining_quantity(self):
        return self.quantity - self.quantity_fulfilled

    def clean(self):
        if self.quantity < 1:
            raise ValidationError("Quantity must be at least 1.")
        if self.product_variant.product_id != self.product.id:
            raise ValidationError("Variant does not match the product.")
        if self.order.tenant_id != self.product.tenant_id:
            raise ValidationError("Product does not belong to the order tenant.")
