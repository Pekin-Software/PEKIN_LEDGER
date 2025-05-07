from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import connection
from .models import Store
from customers.models import Client  # Import Tenant model

@receiver(post_save, sender=Store)
def assign_store_domain(sender, instance, created, **kwargs):
    if created:  # Only assign a domain when a new store is created
        schema_name = connection.schema_name  # Get current tenant schema
        instance.schema_name = schema_name  # Assign schema name

        try:
            tenant = Client.objects.get(schema_name=schema_name)  # Get tenant object
            tenant_domain = tenant.get_domain()  # Fetch the actual domain

            if tenant_domain:  # Ensure a domain exists before assigning
                instance.domain_name = f"{instance.store_name.lower()}.{tenant_domain}"
                instance.save()
        except Client.DoesNotExist:
            pass  # Handle cases where the tenant is not found
