from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Client

@receiver(post_save, sender=Client)
def create_schema(sender, instance, created, **kwargs):
    """Automatically create schema when a new tenant is created."""
    if created:
        instance.create_schema(check_if_exists=True)
