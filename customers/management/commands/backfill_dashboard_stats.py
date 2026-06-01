# customers/management/commands/backfill_dashboard_stats.py
from django.core.management.base import BaseCommand
from django.db import transaction
from customers.models import Client  # your tenant model
from sales.models import Sale
from sales.utils import apply_sale_stats
from django_tenants.utils import schema_context  # if using django-tenants

class Command(BaseCommand):
    help = "Backfill DashboardMonthlyStat for all tenants"

    def handle(self, *args, **options):
        self.stdout.write("Starting backfill of DashboardMonthlyStat...")

        tenants = Client.objects.all()
        self.stdout.write(f"Found {tenants.count()} tenants.")

        for tenant in tenants:
            self.stdout.write(f"\nProcessing tenant: {tenant.business_name} (ID: {tenant.id})")

            try:
                with schema_context(tenant.schema_name):  # switch to tenant schema
                    sales = Sale.objects.all().order_by('sale_date')
                    self.stdout.write(f"  Found {sales.count()} sales for tenant {tenant.business_name}")

                    for sale in sales:
                        try:
                            with transaction.atomic():
                                apply_sale_stats(sale)
                        except Exception as e:
                            self.stderr.write(f"    ERROR applying stats for sale {sale.id}: {e}")
                    
                    self.stdout.write(f"  Done tenant {tenant.business_name}")
            except Exception as e:
                self.stderr.write(f"Failed processing tenant {tenant.business_name}: {e}")

        self.stdout.write("\nBackfill completed successfully!")
