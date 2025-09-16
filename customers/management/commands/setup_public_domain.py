from django.core.management.base import BaseCommand
from customers.models import Client, Domain

class Command(BaseCommand):
    help = "Ensure public tenant and domain are created"

    def handle(self, *args, **kwargs):
        if not Client.objects.filter(schema_name="public").exists():
            tenant = Client(schema_name="public", business_name="Public")
            tenant.save()
            self.stdout.write(self.style.SUCCESS("Created public tenant."))
        else:
            tenant = Client.objects.get(schema_name="public")
            self.stdout.write("Public tenant already exists.")

        domain, created = Domain.objects.get_or_create(
            domain="api.pekingledger.com",
            tenant=tenant,
            defaults={"is_primary": True}
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"Created domain: {domain.domain}"))
        else:
            self.stdout.write(f"Domain already exists: {domain.domain}")
