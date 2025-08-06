from django.db import models
from customers.models import Client
from products.models import Product, ProductLot, ProductVariant
from stores.models import Store
import uuid
from django.utils import timezone
from rest_framework.exceptions import ValidationError

#Warehouse
class Warehouse(models.Model):
    tenant = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="warehouses")  # Link warehouse to tenant (Client)
    warehouse_uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    warehouse_id = models.CharField(max_length=20, unique=True, blank=True)
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=255)
    warehouse_type = models.CharField(max_length=50, choices=[('general', 'General'), ('store', 'Store')])
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="warehouses", null=True, blank=True)  # Store warehouse linked to Store
    
    def save(self, *args, **kwargs):
        if not self.warehouse_id:  # Only set ID if it's not already set
            last_warehouse = Warehouse.objects.filter(tenant=self.tenant).order_by('-id').first()
            if last_warehouse and last_warehouse.warehouse_id.startswith("WH-"):
                last_number = int(last_warehouse.warehouse_id.split("-")[1])
                new_number = last_number + 1
            else:
                new_number = 1

            # Format warehouse ID
            if new_number < 100:
                self.warehouse_id = f"WH-{new_number:03d}"  # WH-001 to WH-099
            else:
                self.warehouse_id = f"WH-{new_number}"  # WH-100, WH-101, etc.

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.warehouse_id} - {self.name}"
    def is_general(self):
        return self.warehouse_type == 'general'
    
class Section(models.Model):
    warehouse = models.ForeignKey(Warehouse, related_name="sections", on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    aisle_number = models.CharField(max_length=20, blank=True, null=True)  # Optional: for identifying aisle in warehouse
    shelf_number = models.CharField(max_length=20, blank=True, null=True)  # Optional: for identifying shelf in section

    def __str__(self):
        return f"{self.name} - {self.warehouse.name}"

# Inventory Model (Refers to Lots)
class Inventory(models.Model):
    tenant = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="inventories")  # Link inventory to tenant
    warehouse = models.ForeignKey(Warehouse, related_name="inventories", on_delete=models.CASCADE)
    section = models.ForeignKey(Section, related_name="inventories", on_delete=models.CASCADE)  # Link to Section
    product = models.ForeignKey(Product, related_name="inventories", on_delete=models.CASCADE)
    product_variant = models.ForeignKey(ProductVariant, related_name="inventories", on_delete=models.CASCADE,  null=True, 
    blank=True)
    lot = models.ForeignKey(ProductLot, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    added_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True) 

    class Meta:
        unique_together = ('lot', 'warehouse', 'section')

    indexes = [
            models.Index(fields=['product', 'warehouse']),
    ]

    def __str__(self):
        return f"{self.product.name} in {self.warehouse.name}"
    
    def compute_total_quantity(self):
        if self.warehouse.warehouse_type == 'general':
            return sum(
                lot.quantity
                for variant in self.product.variants.all()
                for lot in variant.lots.all()
            )
        else:
            return self.quantity

    def compute_stock_status(self):
        if not self.product_variant:
            return "Out of Stock"

        lots = self.product_variant.lots.all()
        now = timezone.now().date()

        # Separate non-expired lots
        non_expired_lots = [lot for lot in lots if not lot.expired_date or lot.expired_date >= now]
        total_quantity = sum(lot.quantity for lot in non_expired_lots)
        threshold = self.product.threshold_value or 0

        # If no non-expired lots → Out of Stock (not "Expired" at variant level)
        if total_quantity <= 0:
            return "Out of Stock"
        elif total_quantity <= threshold:
            return "Low Stock"
        return "In Stock"



    def clean(self):
        if self.quantity < 0:
            raise ValidationError("Inventory quantity cannot be negative.")
        if self.tenant != self.warehouse.tenant:
            raise ValidationError("Inventory warehouse tenant mismatch.")
        if self.tenant != self.product.tenant:
            raise ValidationError("Inventory product tenant mismatch.")
        if self.section.warehouse != self.warehouse:
            raise ValidationError("Inventory section does not belong to the specified warehouse.")
        

    def deduct_quantity(self, amount):
        """Reduce the quantity by `amount`, raising an error if not enough stock."""
        if amount > self.quantity:
            raise ValueError("Not enough stock to deduct.")
        self.quantity -= amount
        self.save(update_fields=["quantity", "updated_at"])

    def add_quantity(self, amount):
        """Increase the quantity by `amount`."""
        self.quantity += amount
        self.save(update_fields=["quantity", "updated_at"])
        
    def allocate_to_store(self, store_warehouse, quantity):
        if quantity > self.quantity:
            raise ValueError("Insufficient stock to allocate")
        
        # Deduct quantity from this inventory (general/admin warehouse)
        self.deduct_quantity(quantity)

        # Get or create inventory in the store warehouse for the same product and lot
        section = store_warehouse.sections.first()
        if not section:
            section = Section.objects.create(
                warehouse=store_warehouse,
                name=f"{store_warehouse.name} - Default Section"
            )
        
        store_inventory, created = Inventory.objects.get_or_create(
            tenant=self.tenant,
            warehouse=store_warehouse,
            section=section,
            product=self.product,
            lot=self.lot,
            defaults={'quantity': 0}
        )
        store_inventory.add_quantity(quantity)
        return store_inventory

    def return_from_store(self, store_warehouse, quantity):
        # Find the inventory in the store warehouse
        try:
            store_inventory = Inventory.objects.get(
                tenant=self.tenant,
                warehouse=store_warehouse,
                product=self.product,
                lot=self.lot
            )
        except Inventory.DoesNotExist:
            raise ValueError("No inventory found in store warehouse to return")

        if quantity > store_inventory.quantity:
            raise ValueError("Insufficient stock in store to return")

        # Deduct quantity from store warehouse
        store_inventory.deduct_quantity(quantity)

        # Add quantity back to this inventory (general/admin warehouse)
        self.add_quantity(quantity)
        return store_inventory
        
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


STATUS_PENDING = 'pending'
STATUS_COMPLETED = 'completed'
STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_COMPLETED, 'Completed'),
]

# Transfer Model
class Transfer(models.Model):
    source_warehouse = models.ForeignKey(Warehouse, related_name="outgoing_transfers", on_delete=models.CASCADE)
    destination_warehouse = models.ForeignKey(Warehouse, related_name="incoming_transfers", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name="transfers", on_delete=models.CASCADE)
    quantity = models.IntegerField()
    transfer_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)   
    confirmed_by = models.ForeignKey('customers.User', related_name='confirmed_transfers', null=True, blank=True, on_delete=models.SET_NULL)
    
    def __str__(self):
        return f"Transfer of {self.quantity} {self.product.name} from {self.source_warehouse.name} to {self.destination_warehouse.name}"

# Stock Request Model (Request for stock to be transferred)
class StockRequest(models.Model):
    store = models.ForeignKey(Store, related_name='stock_requests', on_delete=models.CASCADE)
    warehouse_from = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="stock_requests_from")  # General warehouse (source)
    warehouse_to = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="stock_requests_to")  # Store warehouse (destination)
    product = models.ForeignKey(Product, related_name='stock_requests', on_delete=models.CASCADE)
    quantity_requested = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    request_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Stock Request for {self.quantity_requested} {self.product.name} at {self.store.name}."


class ProductSection(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.product.name} in {self.section.name} ({self.quantity} units)"

class TransferLog(models.Model):
    source_inventory = models.ForeignKey(
        'Inventory', 
        related_name='transfers_out', 
        on_delete=models.CASCADE,
        null=True, blank=True
    )
    destination_inventory = models.ForeignKey(
        'Inventory', 
        related_name='transfers_in', 
        on_delete=models.CASCADE,
        null=True, blank=True
    )
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    product_variant = models.ForeignKey('products.ProductVariant', on_delete=models.CASCADE)
    lot = models.ForeignKey('products.ProductLot', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    transferred_at = models.DateTimeField(auto_now_add=True)
    direction = models.CharField(
        max_length=20,
        choices=[('to_store', 'To Store'), ('to_general', 'To General')]
    )
    tenant = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="transferlogs")

