import re
from django.core.exceptions import ValidationError
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Client, Domain

def clean_business_name(name):
    """Ensure the business name contains only valid characters."""
    name = name.strip()
    if not re.match(r'^[a-zA-Z0-9\s]+$', name):
        raise ValidationError("Business name can only contain letters, numbers, and spaces.")
    if len(name) > 100:
        raise ValidationError("Business name must be under 100 characters.")
    return name

def generate_unique_schema_and_domain(name):
    """Generate a unique schema name and domain while preventing conflicts."""
    base_schema = re.sub(r'\s+', '_', name).strip('_')  # Replace spaces with underscores
    base_schema = re.sub(r'[^a-zA-Z0-9_]', '', base_schema)  # Remove special characters

    base_domain = re.sub(r'[^a-zA-Z0-9]+', '', name).lower()  # Remove special characters

    schema_name = base_schema
    domain_url = f"{base_domain}.localhost"
    counter = 1

    # Ensure uniqueness by checking the database
    while Client.objects.filter(schema_name=schema_name).exists() or Domain.objects.filter(domain=domain_url).exists():
        schema_name = f"{base_schema}_{counter}"
        domain_url = f"{base_domain}{counter}.localhost"
        counter += 1

    return schema_name, domain_url

class TenantViewSet(viewsets.ViewSet):
    """
    ViewSet to register tenants dynamically.
    """
    
    @action(detail=False, methods=["post"])
    def register(self, request):
        name = request.data.get("name", "").strip()

        try:
            name = clean_business_name(name)  # Validate name
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Generate unique schema and domain
        schema_name, domain_url = generate_unique_schema_and_domain(name)

        # Create the tenant securely
        try:
            tenant = Client(schema_name=schema_name, name=name)
            tenant.save()

            # Create the domain entry
            domain = Domain(domain=domain_url, tenant=tenant, is_primary=True)
            domain.save()

            return Response({
                "message": "Tenant Created Successfully!",
                "schema_name": schema_name,
                "domain_url": domain_url
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": "An unexpected error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
