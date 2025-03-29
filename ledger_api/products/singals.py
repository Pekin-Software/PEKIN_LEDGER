from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.text import slugify
from .models import Product, Lot, ProductAttribute

@receiver(post_save, sender=Product)
def create_product_slug(sender, instance, **kwargs):
    if not instance.slug:
        instance.slug = slugify(instance.product_name)
        instance.save()

@receiver(post_save, sender=Lot)
def generate_lot_sku(sender, instance, **kwargs):
    if not instance.sku:
        instance.sku = instance.generate_sku()
        instance.save()

@receiver(post_save, sender=ProductAttribute)
def update_product_attributes(sender, instance, **kwargs):
    instance.product.save()
