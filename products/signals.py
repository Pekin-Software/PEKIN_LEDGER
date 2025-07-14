import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Lot, ProductAttribute, Product
from inventory.models import Inventory, Warehouse, Section

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Lot)
def generate_lot_sku(sender, instance, **kwargs):
    if not instance.sku:
        instance.sku = instance.generate_sku()
        instance.save()

@receiver(post_save, sender=ProductAttribute)
def update_product_attributes(sender, instance, **kwargs):
    # Trigger product save to update dependent data if needed
    instance.product.save()

# @receiver(post_save, sender=Lot)
# def create_inventory_for_lot(sender, instance, created, **kwargs):
#     if not created:
#         return

#     product = instance.product
#     tenant = product.tenant

#     # Get tenant's general warehouse
#     warehouse = Warehouse.objects.filter(tenant=tenant, warehouse_type='general').first()
#     if not warehouse:
#         # You can raise error or just log
#         print(f"[WARNING] No general warehouse found for tenant {tenant}")
#         return

#     # Get or create default section
#     section = warehouse.sections.first()
#     if not section:
#         section = Section.objects.create(warehouse=warehouse, name="Default Section")

#     # Check if inventory already exists for same lot
#     if not Inventory.objects.filter(product=product, lot=instance, warehouse=warehouse, section=section).exists():
#         Inventory.objects.create(
#             tenant=tenant,
#             warehouse=warehouse,
#             section=section,
#             product=product,
#             lot=instance,
#             quantity=instance.quantity
#         )
@receiver(pre_save, sender=Lot)
def store_old_quantity_before_lot_update(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._old_quantity = Lot.objects.get(pk=instance.pk).quantity
        except Lot.DoesNotExist:
            instance._old_quantity = 0

# @receiver(post_save, sender=Lot)
# def create_or_update_inventory_for_lot(sender, instance, created, **kwargs):
#     product = instance.product
#     tenant = product.tenant

#     warehouse = Warehouse.objects.filter(tenant=tenant, warehouse_type='general').first()
#     if not warehouse:
#         print(f"[WARNING] No general warehouse found for tenant {tenant}")
#         return

#     section = warehouse.sections.first()
#     if not section:
#         section = Section.objects.create(warehouse=warehouse, name="Default Section")

#     inventory, inv_created = Inventory.objects.get_or_create(
#         product=product,
#         lot=instance,
#         warehouse=warehouse,
#         section=section,
#         defaults={
#             'tenant': tenant,
#             'quantity': instance.quantity
#         }
#     )

#     if not inv_created:
#         old_quantity = getattr(instance, '_old_quantity', instance.quantity)
#         quantity_diff = instance.quantity - old_quantity

#         if quantity_diff != 0:
#             new_quantity = inventory.quantity + quantity_diff
#             if new_quantity < 0:
#                 raise ValueError(
#                     f"Cannot reduce inventory for lot {instance.id}: resulting quantity would be negative."
#                 )
#             inventory.quantity = new_quantity
#             inventory.save()

@receiver(post_save, sender=Lot)
def create_or_update_inventory_for_lot(sender, instance, created, **kwargs):
    product = instance.product
    tenant = product.tenant

    warehouse = Warehouse.objects.filter(tenant=tenant, warehouse_type='general').first()
    if not warehouse:
        print(f"[WARNING] No general warehouse found for tenant {tenant}")
        return

    section = warehouse.sections.first()
    if not section:
        section = Section.objects.create(warehouse=warehouse, name="Default Section")

    inventory, inv_created = Inventory.objects.get_or_create(
        product=product,
        lot=instance,
        warehouse=warehouse,
        section=section,
        defaults={
            'tenant': tenant,
            'quantity': instance.quantity
        }
    )

    if not inv_created:
        old_quantity = getattr(instance, '_old_quantity', instance.quantity)
        quantity_diff = instance.quantity - old_quantity

        if quantity_diff != 0:
            new_quantity = inventory.quantity + quantity_diff
            if new_quantity < 0:
                print(f"[ERROR] Skipping inventory update: would result in negative quantity for lot {instance.id}")
                return  # Skip update instead of raising
            inventory.quantity = new_quantity
            inventory.save()


@receiver(post_save, sender=Product)
def update_inventory_on_product_update(sender, instance, created, **kwargs):
    if created:
        return  # No need on creation (lot will handle it)

    # Update all inventory records tied to this product
    Inventory.objects.filter(product=instance).update(tenant=instance.tenant)

