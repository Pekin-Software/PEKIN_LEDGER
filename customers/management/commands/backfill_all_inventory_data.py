# from django.core.management.base import BaseCommand
# from django_tenants.utils import get_tenant_model, schema_context
# from django.apps import apps

# class Command(BaseCommand):
#     help = "Backfill general warehouses, store warehouses, and inventories for all tenants"

#     def handle(self, *args, **kwargs):
#         Tenant = get_tenant_model()
#         tenants = Tenant.objects.exclude(schema_name="public")

#         for tenant in tenants:
#             self.stdout.write(f"\n🚧 Processing tenant: {tenant.schema_name}")
#             try:
#                 with schema_context(tenant.schema_name):
#                     self.backfill_tenant_data(tenant)
#             except Exception as e:
#                 self.stderr.write(f"❌ Failed for tenant {tenant.schema_name}: {e}")

#         self.stdout.write(self.style.SUCCESS("\n✅ Finished backfilling all tenants."))

#     def backfill_tenant_data(self, tenant):
#         User = apps.get_model('customers', 'User')
#         Warehouse = apps.get_model('inventory', 'Warehouse')
#         Store = apps.get_model('stores', 'Store')
#         Lot = apps.get_model('products', 'Lot')
#         Section = apps.get_model('inventory', 'Section')
#         Inventory = apps.get_model('inventory', 'Inventory')
#         Product = apps.get_model('products', 'Product')

#         # 1. ✅ Create general warehouse if missing
#         if not Warehouse.objects.filter(tenant=tenant, warehouse_type='general').exists():
#             Warehouse.objects.create(
#                 tenant=tenant,
#                 name=f"{tenant.name}'s General Warehouse",
#                 location="Main Distribution Center",
#                 warehouse_type="general"
#             )
#             self.stdout.write(f"✅ Created general warehouse for tenant {tenant.schema_name}")

#         general_warehouse = Warehouse.objects.filter(tenant=tenant, warehouse_type='general').first()
#         if not general_warehouse:
#             self.stderr.write("⚠️ Could not find or create a general warehouse.")
#             return

#         # Ensure general warehouse has at least one section
#         section = general_warehouse.sections.first()
#         if not section:
#             section = Section.objects.create(warehouse=general_warehouse, name="Default Section")
#             self.stdout.write("✅ Created default section for general warehouse")

#         # 2. ✅ Create warehouse for each existing store
#         stores = Store.objects.all()
#         for store in stores:
#             if not Warehouse.objects.filter(store=store, warehouse_type='store').exists():
#                 Warehouse.objects.create(
#                     tenant=tenant,
#                     name=f"{store.store_name} Warehouse",
#                     location=store.address or "Store Location",
#                     warehouse_type="store",
#                     store=store
#                 )
#                 self.stdout.write(f"✅ Created warehouse for store: {store.store_name}")

#         # 3. ✅ Create inventory for each Lot if missing
#         lots = Lot.objects.all()
#         for lot in lots:
#             product = lot.product

#             inventory, created = Inventory.objects.get_or_create(
#                 product=product,
#                 lot=lot,
#                 warehouse=general_warehouse,
#                 section=section,
#                 defaults={
#                     'tenant': tenant,
#                     'quantity': lot.quantity
#                 }
#             )
#             if created:
#                 self.stdout.write(f"🆕 Inventory created for Lot #{lot.id} and Product '{product.name}'")

from django.core.management.base import BaseCommand
from django_tenants.utils import get_tenant_model, schema_context
from django.apps import apps

class Command(BaseCommand):
    help = "Backfill general warehouses, store warehouses, and inventories for all tenants"

    def handle(self, *args, **kwargs):
        Tenant = get_tenant_model()
        tenants = Tenant.objects.exclude(schema_name="public")

        for tenant in tenants:
            self.stdout.write(f"\n🚧 Processing tenant: {tenant.schema_name}")
            try:
                with schema_context(tenant.schema_name):
                    self.backfill_tenant_data()
            except Exception as e:
                self.stderr.write(f"❌ Failed for tenant {tenant.schema_name}: {e}")

        self.stdout.write(self.style.SUCCESS("\n✅ Finished backfilling all tenants."))

    def backfill_tenant_data(self):
        Warehouse = apps.get_model('inventory', 'Warehouse')
        Store = apps.get_model('stores', 'Store')
        Lot = apps.get_model('products', 'Lot')
        Section = apps.get_model('inventory', 'Section')
        Inventory = apps.get_model('inventory', 'Inventory')

        # 1. ✅ Create general warehouse if missing
        general_warehouse = Warehouse.objects.filter(warehouse_type='general').first()
        if not general_warehouse:
            general_warehouse = Warehouse.objects.create(
                name="General Warehouse",
                location="Main Distribution Center",
                warehouse_type="general"
            )
            self.stdout.write("✅ Created general warehouse")

        # Ensure general warehouse has at least one section
        section = general_warehouse.sections.first()
        if not section:
            section = Section.objects.create(warehouse=general_warehouse, name="Default Section")
            self.stdout.write("✅ Created default section for general warehouse")

        # 2. ✅ Create warehouse for each existing store
        stores = Store.objects.all()
        for store in stores:
            if not Warehouse.objects.filter(store=store, warehouse_type='store').exists():
                Warehouse.objects.create(
                    name=f"{store.store_name} Warehouse",
                    location=store.address or "Store Location",
                    warehouse_type="store",
                    store=store
                )
                self.stdout.write(f"✅ Created warehouse for store: {store.store_name}")

        # 3. ✅ Create inventory for each Lot if missing
        lots = Lot.objects.all()
        for lot in lots:
            product = lot.product

            if not Inventory.objects.filter(
                product=product,
                lot=lot,
                warehouse=general_warehouse,
                section=section
            ).exists():
                Inventory.objects.create(
                    product=product,
                    lot=lot,
                    warehouse=general_warehouse,
                    section=section,
                    quantity=lot.quantity
                )
                self.stdout.write(f"🆕 Inventory created for Lot #{lot.id} and Product '{product.name}'")


