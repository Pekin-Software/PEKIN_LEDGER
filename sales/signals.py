from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Payment, Sale

@receiver(post_save, sender=Payment)
def update_sale_status(sender, instance, **kwargs):
    sale = instance.sale
    statuses = list(sale.payments.values_list('status', flat=True))

    if all(s == 'Completed' for s in statuses):
        sale.payment_status = 'Completed'
    elif all(s in ['Failed', 'Cancelled'] for s in statuses):
        sale.payment_status = 'Failed'
        # Reverse inventory only if completely failed (and not already cancelled)
        if sale.payment_status != 'Cancelled':
            sale.reverse_inventory()
    elif any(s == 'Failed' for s in statuses):
        sale.payment_status = 'Processing'
    else:
        sale.payment_status = 'Processing'

    sale.save(update_fields=['payment_status'])


@receiver([post_save, post_delete], sender=Payment)
def update_sale_payment_totals(sender, instance, **kwargs):
    sale = instance.sale
    sale.update_payment_totals(skip_if_cancelled=True)
