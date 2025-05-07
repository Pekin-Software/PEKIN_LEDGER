from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Transfer, Inventory, StockRequest


@receiver(post_save, sender=Transfer)
def update_inventory_on_transfer(sender, instance, created, **kwargs):
    if created and instance.is_confirmed:
        # Deduct quantity from source warehouse
        from_inventory = Inventory.objects.filter(warehouse=instance.source_warehouse, product=instance.product).order_by('lot__purchase_date')
        
        quantity_left = instance.quantity
        for inventory in from_inventory:
            if quantity_left <= 0:
                break
            if inventory.quantity <= quantity_left:
                quantity_left -= inventory.quantity
                inventory.deduct_quantity(inventory.quantity)
            else:
                inventory.deduct_quantity(quantity_left)
                quantity_left = 0

        # Add to destination warehouse
        to_inventory, created = Inventory.objects.get_or_create(
            warehouse=instance.destination_warehouse, product=instance.product, lot=from_inventory.last().lot
        )
        to_inventory.quantity += instance.quantity
        to_inventory.save()

@receiver(post_save, sender=StockRequest)
def handle_stock_request(sender, instance, created, **kwargs):
    if created and instance.status == 'approved':
        # Perform action, e.g., initiate transfer or update inventory
        # This is just an example; modify it as per your requirements.
        print(f"Stock request approved for {instance.quantity_requested} of {instance.product.name} at {instance.store.name}")
