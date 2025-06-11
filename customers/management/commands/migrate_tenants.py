from django.core.management.base import BaseCommand
from django.db import connection
from django.core.management import call_command
from customers.models import Client 

class Command(BaseCommand):
    help = 'Run migrations on all tenant schemas'

    def handle(self, *args, **kwargs):
        for tenant in Client.objects.all():
            self.stdout.write(f"Migrating schema: {tenant.schema_name}")
            connection.set_schema(tenant.schema_name)
            call_command('migrate', interactive=False)
        self.stdout.write(self.style.SUCCESS('Migrations completed for all tenants.'))
