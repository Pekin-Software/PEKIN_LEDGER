from django.db import models
from customers.models import Client
from products.models import Product, Lot
from stores.models import Store
import uuid
from django.utils import timezone
from django.db.models import Sum

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
    lot = models.ForeignKey(Lot, related_name="inventories", on_delete=models.CASCADE)  # Linking to a specific lot
    quantity = models.IntegerField()
    added_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True) 

    class Meta:
        unique_together = ('warehouse', 'section', 'product', 'lot')  # Prevent duplicate inventory entries
        indexes = [
            models.Index(fields=['product', 'warehouse']),
        ]

    def __str__(self):
        return f"{self.product.name} in {self.warehouse.name} (Lot {self.lot.id})"

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

class ProductMovement(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    from_section = models.ForeignKey(Section, related_name="movements_from", on_delete=models.CASCADE)
    to_section = models.ForeignKey(Section, related_name="movements_to", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    movement_date = models.DateTimeField(auto_now_add=True)

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.from_section.warehouse != self.to_section.warehouse:
            raise ValidationError("Both sections must belong to the same warehouse.")

    def save(self, *args, **kwargs):
        if self.from_section.warehouse != self.to_section.warehouse:
            raise ValueError("Sections must belong to the same warehouse.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Moved {self.quantity} of {self.product.name} from {self.from_section.name} to {self.to_section.name}"

