from django.core.management.base import BaseCommand
from django.db import connection
from customers.models import Client

class Command(BaseCommand):
    help = "Remove tenant records that point to missing schemas in the database"

    def handle(self, *args, **kwargs):
        deleted_count = 0

        for tenant in Client.objects.all():
            if not self.schema_exists(tenant.schema_name):
                self.stderr.write(f"❌ Missing schema for tenant: {tenant.schema_name}. Deleting tenant record...")
                tenant.delete()
                deleted_count += 1

        if deleted_count == 0:
            self.stdout.write(self.style.SUCCESS("✅ All tenant schemas are valid. Nothing to clean."))
        else:
            self.stdout.write(self.style.SUCCESS(f"✅ Removed {deleted_count} invalid tenant(s)."))

    def schema_exists(self, schema_name):
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.schemata WHERE schema_name = %s
                )
            """, [schema_name])
            return cursor.fetchone()[0]
