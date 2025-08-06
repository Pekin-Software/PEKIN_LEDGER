import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ProductVariant

logger = logging.getLogger(__name__)

@receiver(post_save, sender=ProductVariant)
def generate_sku(sender, instance, created, **kwargs):
    if created and not instance.sku:
        instance.sku = instance.generate_sku()
        instance.save(update_fields=['sku'])
        logger.info(f"Generated SKU {instance.sku} for ProductVariant id {instance.pk}")
