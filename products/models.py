from django.db import models, IntegrityError
from django.utils.text import slugify
from customers.models import Client
from django.utils import timezone 
import uuid
import random
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
from django.core.files.base import ContentFile
   
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    tenant = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="products")
    product_name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True, max_length=300)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
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

    class Meta:
        unique_together = ('tenant', 'product_name', 'category')

    def __str__(self):
        return self.product_name

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

class ProductVariant(models.Model):
    product = models.ForeignKey(Product, related_name="variants", on_delete=models.CASCADE)
    sku = models.CharField(max_length=50, unique=True, blank=True)
    barcode = models.CharField(max_length=50, unique=True, blank=True)
    barcode_image = models.ImageField(upload_to='barcodes/', null=True, blank=True)

    def __str__(self):
        attrs = ", ".join([val.value for val in self.attributes.all()])
        return f"{self.product.product_name} ({attrs})"
    def get_variant_label(self, obj):
        attrs = obj.attributes.all()
        attr_str = ", ".join(f"{attr.name}: {attr.value}" for attr in attrs)
        return f"{obj.product.product_name} — {attr_str}"
    
    def generate_sku(self):
        base = slugify(self.product.product_name)[:5].upper()
        unique_id = uuid.uuid4().hex[:6].upper()
        return f"{base}-{unique_id}"

    def generate_barcode(self):
        while True:
            barcode = ''.join([str(random.randint(0, 9)) for _ in range(12)])
            if not ProductVariant.objects.filter(barcode=barcode).exists():
                return barcode
            
    def generate_barcode_image(self):
        EAN = barcode.get_barcode_class('ean13')  # or 'code128'
        number = self.barcode  # must be 12 digits for ean13
        
        ean = EAN(number, writer=ImageWriter())
        buffer = BytesIO()
        ean.write(buffer)
        self.barcode_image.save(f'{self.barcode}.png', ContentFile(buffer.getvalue()), save=False)

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = self.generate_sku()
        if not self.barcode:
            # Retry loop in case of race condition
            for _ in range(5):  # retry up to 5 times
                self.barcode = self.generate_barcode()
                try:
                    super().save(*args, **kwargs)
                    break
                except IntegrityError:
                    self.barcode = None  # retry with new barcode
            else:
                raise IntegrityError("Failed to generate a unique barcode after multiple attempts.")
        else:
            super().save(*args, **kwargs)

        if not self.barcode_image:
            self.generate_barcode_image()
            super().save(update_fields=['barcode_image'])
    @property
    def total_quantity(self):
        return self.lots.aggregate(total=models.Sum('quantity'))['total'] or 0

class VariantAttribute(models.Model):
    variant = models.ForeignKey(ProductVariant, related_name="attributes", on_delete=models.CASCADE)
    name = models.CharField(max_length=100)  # e.g., "Color"
    value = models.CharField(max_length=255)  # e.g., "Red"

    class Meta:
        unique_together = ('variant', 'name')

    def __str__(self):
        return f"{self.name}: {self.value}"
    
class ProductLot(models.Model):
    variant = models.ForeignKey(ProductVariant, related_name="lots", on_delete=models.CASCADE)
    lot_number = models.CharField(max_length=50, unique=True, blank=True)
    quantity = models.PositiveIntegerField()
    expired_date = models.DateField(null=True, blank=True)

    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    wholesale_quantity = models.PositiveIntegerField(default=0)
    wholesale_selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    retail_selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    purchase_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('variant', 'lot_number')

    def __str__(self):
        return f"Lot {self.lot_number or self.id} - {self.variant}"
    
    def lot_purchase_cost(self):
        return self.purchase_price * self.quantity

    def generate_lot_number(self):
        unique_id = uuid.uuid4().hex[:6].upper()
        return f"LOT-{unique_id}"

    def save(self, *args, **kwargs):
        if not self.lot_number:
            self.lot_number = self.generate_lot_number()
        super().save(*args, **kwargs)




