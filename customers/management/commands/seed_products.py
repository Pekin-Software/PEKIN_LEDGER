from django.db import transaction
from customers.models import Client
from products.models import Product, ProductVariant, VariantAttribute, Category
from products.serializers import ProductLotSerializer
from django.core.management.base import BaseCommand

# Configuration: define products, variants, attributes, lots
PRODUCTS_CONFIG = [
    {
        "name": "Widget Pro",
        "unit": "pcs",
        "currency": "USD",
        "variants": [
            {
                "attributes": {"Color": "Red", "Size": "M"},
                "lots": [
                    {"quantity": 100, "purchase_price": 10.0, "retail_selling_price": 15.0},
                    {"quantity": 50, "purchase_price": 9.5, "retail_selling_price": 14.0}
                ]
            },
            {
                "attributes": {"Color": "Blue", "Size": "L"},
                "lots": [
                    {"quantity": 60, "purchase_price": 12.0, "retail_selling_price": 18.0}
                ]
            },
        ]
    },
    {
        "name": "Gadget Max",
        "unit": "pcs",
        "currency": "USD",
        "variants": [
            {
                "attributes": {"Color": "Black"},
                "lots": [
                    {"quantity": 200, "purchase_price": 15.0, "retail_selling_price": 22.0}
                ]
            }
        ]
    }
]
def seed_tenant_products(tenant: Client):
    """
    Seed multiple products, variants, lots, and inventory for a given tenant.
    Skips tenant if they have no categories.
    """
    # Pick the first category for this tenant
    category = Category.objects.filter(tenant=tenant).first()
    if not category:
        print(f"Skipping tenant '{tenant.schema_name}' – no category found.")
        return

    for product_data in PRODUCTS_CONFIG:
        product_name = product_data["name"]

        if Product.objects.filter(tenant=tenant, product_name=product_name, category=category).exists():
            continue

        product = Product.objects.create(
            tenant=tenant,
            product_name=product_name,
            category=category,
            unit=product_data.get("unit", "pcs"),
            currency=product_data.get("currency", "USD")
        )

        for variant_data in product_data.get("variants", []):
            variant = ProductVariant.objects.create(product=product)

            for attr_name, attr_value in variant_data.get("attributes", {}).items():
                VariantAttribute.objects.create(variant=variant, name=attr_name, value=attr_value)

            for lot_info in variant_data.get("lots", []):
                lot_info["variant"] = variant
                serializer = ProductLotSerializer(data=lot_info)
                serializer.is_valid(raise_exception=True)
                serializer.save()

def seed_all_tenants():
    tenants = Client.objects.all()
    for tenant in tenants:
        print(f"Seeding tenant: {tenant.schema_name}")
        seed_tenant_products(tenant)
        print(f"Finished seeding tenant: {tenant.schema_name}")


class Command(BaseCommand):
    help = "Seed products, variants, lots, and inventory for all tenants"

    def handle(self, *args, **kwargs):
        with transaction.atomic():
            seed_all_tenants()
        self.stdout.write(self.style.SUCCESS("All tenants seeded successfully."))
