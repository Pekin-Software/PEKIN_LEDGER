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

# python3 manage.py migrate_schemas --shared && python3 manage.py migrate_tenants && python manage.py setup_public_domain && python3 manage.py backfill_all_inventory_data && python3 manage.py collectstatic --noinput && gunicorn ledger_api.wsgi:application