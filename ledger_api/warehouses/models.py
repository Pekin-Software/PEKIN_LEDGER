# from django.db import models
# from customers.models import TenantMixin

# class Warehouse(TenantMixin):
#     warehouse_id = models.CharField(max_length=10, unique=True, editable=False)
#     name = models.CharField(max_length=100)
#     location = models.CharField(max_length=255)

#     def save(self, *args, **kwargs):
#         if not self.warehouse_id:  # Only set ID if it's not already set
#             last_warehouse = Warehouse.objects.filter(tenant=self.tenant).order_by('-id').first()
#             if last_warehouse and last_warehouse.warehouse_id.startswith("WH-"):
#                 last_number = int(last_warehouse.warehouse_id.split("-")[1])
#                 new_number = last_number + 1
#             else:
#                 new_number = 1

#             # Format warehouse ID
#             if new_number < 100:
#                 self.warehouse_id = f"WH-{new_number:03d}"  # WH-001 to WH-099
#             else:
#                 self.warehouse_id = f"WH-{new_number}"  # WH-100, WH-101, etc.

#         super().save(*args, **kwargs)

#     def __str__(self):
#         return f"{self.warehouse_id} - {self.name}"
    
# class Section(models.Model):
#     warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='sections')
#     name = models.CharField(max_length=50)  # Example: "Cold Storage", "Aisle 1"
#     description = models.TextField(blank=True, null=True)

#     def __str__(self):
#         return f"{self.name} ({self.warehouse.name})"