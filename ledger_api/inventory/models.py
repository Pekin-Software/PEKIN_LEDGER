# from django.db import models
# from django.utils.text import slugify

# class Product(models.Model):
#     sku = models.CharField(max_length=20, unique=True, blank=True)
#     product_name = models.CharField(max_length=255)
#     category = models.ForeignKey('Category', on_delete=models.CASCADE, related_name='products')
#     unit = models.CharField(max_length=50)
#     quantity = models.PositiveIntegerField(default=0)
#     price = models.DecimalField(max_digits=10, decimal_places=2)
#     expired_date = models.DateField(null=True, blank=True)
#     threshold_value = models.PositiveIntegerField(default=0)
#     product_image = models.ImageField(upload_to='product_images/', null=True, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#     warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='products')
#     section = models.ForeignKey(Section, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')

#     def __str__(self):
#         return self.product_name
    
#     @property
#     def stock_status(self):
#         return "In Stock" if self.quantity > 0 else "Out of Stock"

#     def generate_sku(self):
#         category_code = self.category.name[:3].upper()  # First 3 letters of Category
#         product_id = self.id if self.id else "XXX"  # Placeholder if ID not assigned yet

#         # Collect attributes (e.g., Color, Size)
#         attributes = "-".join(
#             [attr.value[:3].upper() for attr in self.attributes.all()]
#         ) if self.attributes.exists() else ""

#         sku = f"{category_code}-{attributes}-{product_id}" if attributes else f"{category_code}-{product_id}"
#         return slugify(sku).upper()

#     def save(self, *args, **kwargs):
#         if not self.sku:  # Generate SKU only if not set
#             self.sku = self.generate_sku()
#         super().save(*args, **kwargs)

# class ProductAttribute(models.Model):
#     product = models.ForeignKey(Product, related_name='attributes', on_delete=models.CASCADE)
#     name = models.CharField(max_length=100)  # e.g., 'Color', 'Memory', 'Screen Size'
#     value = models.CharField(max_length=255)  # e.g., 'Black', '128GB', '6.5 inches'

#     def __str__(self):
#         return f"{self.name}: {self.value}"
    
# class Category(models.Model):
#     name = models.CharField(max_length=100, unique=True)
#     description = models.TextField(blank=True, null=True)

#     def __str__(self):
#         return self.name