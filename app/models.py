from django_tenants.models import TenantMixin, DomainMixin
from django.db import models

class Client(TenantMixin):
    name = models.CharField(max_length=255)
    schema_name = models.CharField(max_length=50, unique=True)  # Unique schema name
    created_on = models.DateField(auto_now_add=True)

    # Default schema settings
    auto_create_schema = True

class Domain(DomainMixin):
    pass
