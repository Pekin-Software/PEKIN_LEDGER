from decimal import Decimal

from django.db import transaction

from inventory.models import (
    Inventory,
    InventoryMovement,
    Section,
    Purchase
)

from products.models import ProductLot
from taxation.models import VATLedger
from accounting.services.journal_services import JournalService


class PurchasePostingService:

    @staticmethod
    @transaction.atomic
    def post_purchase(purchase_id, user=None):

        purchase = (
            Purchase.objects
            .select_for_update()
            .select_related("tenant", "store_name", "supplier")
            .prefetch_related("items__product", "items__product_variant")
            .get(id=purchase_id)
        )

        if purchase.is_posted:
            raise ValueError("Purchase already posted.")

        duplicate_invoice = (
            Purchase.objects.filter(
                tenant=purchase.tenant,
                invoice_number=purchase.invoice_number
            )
            .exclude(id=purchase.id)
            .exists()
        )

        if duplicate_invoice:
            raise ValueError("Duplicate supplier invoice.")

        warehouse = purchase.store_name.warehouses.filter(
            tenant=purchase.tenant
        ).first()

        if not warehouse:
            raise ValueError("Store has no warehouse.")

        section = warehouse.sections.first()

        if not section:
            section = Section.objects.create(
                warehouse=warehouse,
                name="Default Section"
            )

        subtotal = Decimal("0.00")
        vat_total = Decimal("0.00")

        for item in purchase.items.all():

            subtotal += item.subtotal
            vat_total += item.vat_amount

            product = item.product
            incoming_qty = Decimal(item.quantity)
            incoming_cost = Decimal(item.unit_cost)

            current_stock = Decimal(product.total_quantity or 0)
            current_avg_cost = Decimal(product.average_cost or 0)

            lot = ProductLot.objects.create(
                variant=item.product_variant,
                warehouse=warehouse,
                purchase_item=item,
                quantity=item.quantity,
                purchase_price=item.unit_cost,
                purchase_date=purchase.invoice_date
            )

            inventory, created = Inventory.objects.get_or_create(
                tenant=purchase.tenant,
                warehouse=warehouse,
                section=section,
                product=product,
                product_variant=item.product_variant,
                lot=lot,
                defaults={"quantity": item.quantity}
            )

            if not created:
                inventory.quantity += item.quantity
                inventory.save(update_fields=["quantity", "updated_at"])

            total_existing_cost = current_stock * current_avg_cost
            total_new_cost = incoming_qty * incoming_cost
            denominator = current_stock + incoming_qty

            product.average_cost = (
                (total_existing_cost + total_new_cost) / denominator
                if denominator > 0
                else incoming_cost
            )
            product.total_quantity = current_stock + incoming_qty
            product.save(update_fields=["average_cost", "total_quantity"])

            InventoryMovement.objects.create(
                tenant=purchase.tenant,
                warehouse=warehouse,
                product=product,
                product_variant=item.product_variant,
                lot=lot,
                purchase=purchase,
                movement_type="PURCHASE",
                quantity=item.quantity,
                unit_cost=item.unit_cost,
                total_cost=item.subtotal,
                reference=purchase.invoice_number,
                remarks="Purchase Posting"
            )

            if item.vat_amount > 0:
                VATLedger.objects.create(
                    tenant=purchase.tenant,
                    vat_type="INPUT",
                    transaction_reference=purchase.invoice_number,
                    taxable_amount=item.subtotal,
                    vat_rate=item.vat_rate,
                    vat_amount=item.vat_amount,
                    reporting_period=purchase.created_at.strftime("%Y-%m")
                )

        purchase.subtotal = subtotal
        purchase.vat_total = vat_total
        purchase.grand_total = subtotal + vat_total

        journal_id = JournalService.create_purchase_journal(purchase)

        purchase.journal_entry_id = journal_id
        purchase.is_posted = True
        purchase.status = "POSTED"

        purchase.save(update_fields=[
            "subtotal",
            "vat_total",
            "grand_total",
            "journal_entry_id",
            "is_posted",
            "status"
        ])

        return purchase