from django.db import models
from django.utils.text import slugify
from customers.models import Client
from django.utils import timezone 
import uuid
from django.db.models import Sum

class Product(models.Model):
    tenant = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="products")
    product_name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True, max_length=300)
    category = models.ForeignKey('Category', on_delete=models.CASCADE, related_name='products')
    unit = models.CharField(max_length=50, null=True, blank=True)
    threshold_value = models.PositiveIntegerField(default=0)
    product_image = models.ImageField(upload_to='product_images/', null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    CURRENCY_CHOICES = [
        ('USD', 'US Dollars'),
        ('LRD', 'Liberian Dollars'),
    ]
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='LRD')

    def __str__(self):
        return self.product_name

    @property
    def total_quantity(self):
        return self.lots.aggregate(total=models.Sum('quantity'))['total'] or 0
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.product_name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class ProductAttribute(models.Model):
    product = models.ForeignKey(Product, related_name='attributes', on_delete=models.CASCADE, null=True)
    name = models.CharField(max_length=100)  # e.g., 'Color', 'Memory', 'Screen Size'
    value = models.CharField(max_length=255)  # e.g., 'Black', '128GB', '6.5 inches'

    def __str__(self):
        return f"{self.name}: {self.value}"
    
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name
    
class Lot(models.Model):
    product = models.ForeignKey(Product, related_name="lots", on_delete=models.CASCADE, null=True)
    sku = models.CharField(max_length=50, unique=True, blank=True)

    # Stock & Expiry
    quantity = models.PositiveIntegerField()  # Number of units in this batch
    expired_date = models.DateField(null=True, blank=True)  # Expiration date

    # Pricing
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Price when purchased in bulk
    wholesale_quantity = models.PositiveIntegerField(default=0) 
    wholesale_selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Selling price for bulk buyers
    retail_selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Selling price for individual customers
    
    # Timestamps
    purchase_date = models.DateField(null=True, blank=True)  # Date of purchase
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Lot {self.id} - {self.product.product_name}"

    def cost_of_lot(self):
        """Calculates the total cost of the lot based on wholesale purchase price."""
        return self.wholesale_purchase_price * self.quantity

    def generate_sku(self):
        """Generates a unique SKU for the lot."""
        category_code = self.product.category.name[:3].upper()
        unique_id = uuid.uuid4().hex[:6].upper()
        return slugify(f"{category_code}-{unique_id}").upper()
    
    def save(self, *args, **kwargs):
        if not self.sku:  # Generate SKU if not set
            self.sku = self.generate_sku()
        super().save(*args, **kwargs)
 