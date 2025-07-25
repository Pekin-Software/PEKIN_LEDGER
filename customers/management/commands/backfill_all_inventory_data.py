
from django.core.management.base import BaseCommand
from django_tenants.utils import get_tenant_model, schema_context
from django.apps import apps
from django.utils import timezone

class Command(BaseCommand):
    help = "Backfill general warehouses, store warehouses, and inventories for all tenants"

    def handle(self, *args, **kwargs):
        Tenant = get_tenant_model()
        tenants = Tenant.objects.exclude(schema_name="public")

        for tenant in tenants:
            self.stdout.write(f"\n🚧 Processing tenant: {tenant.schema_name}")
            try:
                with schema_context(tenant.schema_name):
                    self.backfill_tenant_data(tenant)
            except Exception as e:
                self.stderr.write(f"❌ Failed for tenant {tenant.schema_name}: {e}")

        self.stdout.write(self.style.SUCCESS("\n✅ Finished backfilling all tenants."))

    # def backfill_tenant_data(self, tenant):
    #     Warehouse = apps.get_model('inventory', 'Warehouse')
    #     Store = apps.get_model('stores', 'Store')
    #     Lot = apps.get_model('products', 'Lot')
    #     Section = apps.get_model('inventory', 'Section')
    #     Inventory = apps.get_model('inventory', 'Inventory')
    #     Product = apps.get_model('products', 'Product')

    #     # 1. ✅ Create general warehouse if missing
    #     general_warehouse = Warehouse.objects.filter(warehouse_type='general').first()
    #     if not general_warehouse:
    #         general_warehouse = Warehouse.objects.create(
    #             name="General Warehouse",
    #             location="Main Distribution Center",
    #             warehouse_type="general",
    #             tenant=tenant
    #         )
    #         self.stdout.write("✅ Created general warehouse")

    #     # Ensure general warehouse has at least one section
    #     section = general_warehouse.sections.first()
    #     if not section:
    #         section = Section.objects.create(
    #             warehouse=general_warehouse,
    #             name="Default Section"
    #         )
    #         self.stdout.write("✅ Created default section for general warehouse")

    #     # 2. ✅ Create warehouse for each existing store
    #     stores = Store.objects.all()
    #     for store in stores:
    #         if not Warehouse.objects.filter(store=store, warehouse_type='store').exists():
    #             Warehouse.objects.create(
    #                 name=f"{store.store_name} Warehouse",
    #                 location=store.address or "Store Location",
    #                 warehouse_type="store",
    #                 store=store,
    #                 tenant=tenant
    #             )
    #             self.stdout.write(f"✅ Created warehouse for store: {store.store_name}")

    #     # 3. ✅ Create inventory for each Lot if missing
    #     lots = Lot.objects.all()
    #     for lot in lots:
    #         product = lot.product

    #         if not Inventory.objects.filter(
    #             product=product,
    #             lot=lot,
    #             warehouse=general_warehouse,
    #             section=section
    #         ).exists():
    #             Inventory.objects.create(
    #                 tenant=tenant,
    #                 product=product,
    #                 lot=lot,
    #                 warehouse=general_warehouse,
    #                 section=section,
    #                 quantity=lot.quantity,
    #                 added_at=timezone.now()
    #             )
    #             self.stdout.write(f"🆕 Inventory created for Lot #{lot.id} and Product '{product.name}'")

    def backfill_tenant_data(self, tenant):
        Warehouse = apps.get_model('inventory', 'Warehouse')
        Store = apps.get_model('stores', 'Store')
        Lot = apps.get_model('products', 'Lot')
        Section = apps.get_model('inventory', 'Section')
        Inventory = apps.get_model('inventory', 'Inventory')
        Product = apps.get_model('products', 'Product')

        # ✅ Always filter general warehouse by tenant
        general_warehouse = Warehouse.objects.filter(
            warehouse_type='general',
            tenant=tenant
        ).first()

        if not general_warehouse:
            general_warehouse = Warehouse.objects.create(
                name="General Warehouse",
                location="Main Distribution Center",
                warehouse_type="general",
                tenant=tenant
            )
            self.stdout.write("✅ Created general warehouse")

        # ✅ Ensure the section is linked to this general warehouse
        section = Section.objects.filter(warehouse=general_warehouse).first()
        if not section:
            section = Section.objects.create(
                warehouse=general_warehouse,
                name="Default Section"
            )
            self.stdout.write("✅ Created default section for general warehouse")

        # ✅ Create warehouse for each store
        stores = Store.objects.all()
        for store in stores:
            if not Warehouse.objects.filter(store=store, warehouse_type='store', tenant=tenant).exists():
                Warehouse.objects.create(
                    name=f"{store.store_name} Warehouse",
                    location=store.address or "Store Location",
                    warehouse_type="store",
                    store=store,
                    tenant=tenant
                )
                self.stdout.write(f"✅ Created warehouse for store: {store.store_name}")

        # ✅ Create inventory for each Lot in current schema
        lots = Lot.objects.select_related('product').all()
        created_count = 0

        for lot in lots:
            product = lot.product

            # double check all identifiers: tenant's warehouse, lot, section, product
            if not Inventory.objects.filter(
                product=product,
                lot=lot,
                warehouse=general_warehouse,
                section=section,
                tenant=tenant
            ).exists():
                Inventory.objects.create(
                    tenant=tenant,
                    product=product,
                    lot=lot,
                    warehouse=general_warehouse,
                    section=section,
                    quantity=lot.quantity
                )
                created_count += 1
                self.stdout.write(f"🆕 Inventory created for Lot #{lot.id} and Product '{product. product_name}'")

        self.stdout.write(f"✅ Inventory backfill complete: {created_count} new inventory records created.")



