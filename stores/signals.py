from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import connection
from .models import Store
from inventory.models import Warehouse
from customers.models import Client  

@receiver(post_save, sender=Store)
def create_store_warehouse(sender, instance, created, **kwargs):
    if created:
        Warehouse.objects.create(
            tenant=instance.tenant,
            name=f"{instance.store_name} Warehouse",
            location=instance.address or "Store Location",
            warehouse_type="store",
            store=instance
        )
