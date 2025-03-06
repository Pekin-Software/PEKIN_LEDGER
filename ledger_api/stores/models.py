from django.db import models
from django.db import connection 
from customers.models import User  # Assuming User model is in the 'customer' app

class Store(models.Model):
    schema_name = models.CharField(max_length=100, blank=True, null=True)
    store_name = models.CharField(max_length=100)
    location = models.CharField(max_length=255)

    def save(self, *args, **kwargs):
        if not self.schema_name:  
            self.schema_name = connection.schema_name  # Assign tenant schema
        super().save(*args, **kwargs)
        
    def __str__(self):
        return self.store_name

class Employee(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='employees')
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='employees')
    date_assigned = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.store.store_name} ({self.user.position})"  # Accessing position from User model

    class Meta:
        unique_together = ('store', 'user')


# class StoreProduct(models.Model):
#     store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='store_products')
#     produc_name = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='store_products')
#     category = models.ForeignKey('Category', on_delete=models.CASCADE, related_name='products')
#     unit = models.CharField(max_length=50)
#     quantity = models.PositiveIntegerField(default=0)
#     price = models.DecimalField(max_digits=10, decimal_places=2)
#     expired_date = models.DateField(null=True, blank=True)
#     threshold_value = models.PositiveIntegerField(default=0)
#     product_image = models.ImageField(upload_to='product_images/', null=True, blank=True)
#     added_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#     warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='products')
#     section = models.ForeignKey(Section, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
#     def __str__(self):
#         return f"{self.product.name} in {self.store.name}"

#     @property
#     def stock_status(self):
#         return "In Stock" if self.quantity > 0 else "Out of Stock"

#     def save(self, *args, **kwargs):
#         if not self.product_id:
#             last_store_product = StoreProduct.objects.order_by('-id').first()
#             next_id = last_store_product.id + 1 if last_store_product else 1
#             self.product_id = f"SP-{next_id:05d}"
#         super().save(*args, **kwargs)


