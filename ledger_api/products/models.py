from django.db import models
from django.utils.text import slugify
from customers.models import Client
from django.utils import timezone 
import uuid
class Product(models.Model):
    tenant = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="products")
    product_name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True, max_length=300)
    category = models.ForeignKey('Category', on_delete=models.CASCADE, related_name='products')
    unit = models.CharField(max_length=50)
    description = models.TextField()
    threshold_value = models.PositiveIntegerField(default=0)
    product_image = models.ImageField(upload_to='product_images/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.product_name
    
    @property
    def stock_status(self):
        active_lots = self.lots.filter(expired_date__gte=timezone.now())  # Ignore expired lots
        total_stock = sum(lot.quantity for lot in active_lots)
        return "In Stock" if total_stock > 0 else "Out of Stock"

    def total_quantity(self):
        """Calculates the total quantity of the product across all lots."""
        return sum(lot.quantity for lot in self.lots.all())
    
    def is_low_stock(self):
        """Checks if the stock level is below the threshold."""
        return self.total_quantity() <= self.threshold_value

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.product_name)
        super().save(*args, **kwargs)


class ProductAttribute(models.Model):
    product = models.ForeignKey(Product, related_name='attributes', on_delete=models.CASCADE)
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
    product = models.ForeignKey(Product, related_name="lots", on_delete=models.CASCADE)
    sku = models.CharField(max_length=50, unique=True, blank=True)

    # Stock & Expiry
    quantity = models.PositiveIntegerField()  # Number of units in this batch
    expired_date = models.DateField(null=True, blank=True)  # Expiration date

    # Pricing
    wholesale_purchase_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Price when purchased in bulk
    retail_purchase_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Price per unit when bought individually
    wholesale_selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Selling price for bulk buyers
    retail_selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Selling price for individual customers

    # Discounts (Multiple discounts can be added)
    wholesale_discount_price = models.ManyToManyField('Discount', related_name="wholesale_discounts", blank=True)
    retail_discount_price = models.ManyToManyField('Discount', related_name="retail_discounts", blank=True)

    # Timestamps
    purchase_date = models.DateTimeField(auto_now_add=True)  # Date of purchase
    created_at = models.DateTimeField(auto_now_add=True)
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

    @property
    def stock_status(self):
        if self.expired_date and self.expired_date < timezone.now():
            return "Expired"
        elif self.quantity > 0:
            return "Available"
        else:
            return "Out of Stock"
    def is_low_stock(self):
        """Checks if the lot's stock is below the threshold."""
        return self.quantity <= self.product.threshold_value
    
    def save(self, *args, **kwargs):
        if not self.sku:  # Generate SKU if not set
            self.sku = self.generate_sku()
        super().save(*args, **kwargs)
    
class Discount(models.Model):
    name = models.CharField(max_length=100)  # e.g., "Black Friday Sale"
    value = models.DecimalField(max_digits=10, decimal_places=2)  # Percentage or fixed amount

    def __str__(self):
        return f"{self.name} ({self.value})"

