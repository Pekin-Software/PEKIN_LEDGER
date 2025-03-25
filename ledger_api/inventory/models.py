from django.db import models
from customers.models import Client
from products.models import Product, Lot
from stores.models import Store

#Warehouse
class Warehouse(models.Model):
    tenant = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="warehouses")  # Link warehouse to tenant (Client)
    warehouse_id = models.CharField(max_length=10, unique=True, editable=False)
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

    def __str__(self):
        return f"{self.product.name} in {self.warehouse.name} (Lot {self.lot.id})"

    def add_quantity(self, qty):
        self.quantity += qty
        self.save()
        
    def deduct_quantity(self, qty):
        self.quantity -= qty
        self.save()

# Transfer Model
class Transfer(models.Model):
    source_warehouse = models.ForeignKey(Warehouse, related_name="outgoing_transfers", on_delete=models.CASCADE)
    destination_warehouse = models.ForeignKey(Warehouse, related_name="incoming_transfers", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name="transfers", on_delete=models.CASCADE)
    quantity = models.IntegerField()
    transfer_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('completed', 'Completed')])    
    confirmed_by = models.ForeignKey('customers.User', related_name='confirmed_transfers', null=True, blank=True, on_delete=models.SET_NULL)
    
    def __str__(self):
        return f"Transfer of {self.quantity} {self.product.name} from {self.from_warehouse.name} to {self.to_warehouse.name}"

# Stock Request Model (Request for stock to be transferred)
class StockRequest(models.Model):
    store = models.ForeignKey(Store, related_name='stock_requests', on_delete=models.CASCADE)
    warehouse_from = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="stock_requests_from")  # General warehouse (source)
    warehouse_to = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="stock_requests_to")  # Store warehouse (destination)
    product = models.ForeignKey(Product, related_name='stock_requests', on_delete=models.CASCADE)
    quantity_requested = models.IntegerField()
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending')
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

    def __str__(self):
        return f"Moved {self.quantity} of {self.product.name} from {self.from_section.name} to {self.to_section.name}"

