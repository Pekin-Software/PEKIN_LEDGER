from decimal import Decimal

from django.db import transaction

from sales.models import Sale
from inventory.models import InventoryMovement
from taxation.models import VATLedger

from accounting.services.journal_services import JournalService


def safe_audit_log(*, user=None, tenant=None, action="", model_name="", object_id=None, old_data=None, new_data=None):
    try:
        from audit.models import AuditLog

        AuditLog.objects.create(
            user=user,
            action=action,
            model_name=model_name,
            object_id=object_id,
            old_data=old_data,
            new_data=new_data,
        )
    except Exception:
        pass


def safe_compliance_hook(*, tenant=None, source=None, instance=None):
    try:
        from compliance.services import ComplianceEngine

        ComplianceEngine.evaluate_transaction(
            tenant=tenant,
            source=source,
            instance=instance
        )
    except Exception:
        pass


def safe_reconciliation_hook(*, tenant=None, sale=None):
    try:
        from reconciliation.services import ReconciliationEngine

        ReconciliationEngine.register_sale_for_reconciliation(
            tenant=tenant,
            sale=sale
        )
    except Exception:
        pass


class SalesPostingService:

    @staticmethod
    @transaction.atomic
    def post_sale(sale_id, user=None):

        sale = (
            Sale.objects
            .select_for_update()
            .select_related("tenant", "store", "cashier")
            .prefetch_related("sale_details__product", "sale_details__product_variant", "sale_details__lot")
            .get(id=sale_id)
        )

        if sale.is_posted:
            raise ValueError("Sale already posted.")

        subtotal = Decimal("0.00")
        vat_total = Decimal("0.00")
        total_cogs = Decimal("0.00")

        for item in sale.sale_details.all():

            subtotal += item.subtotal
            vat_total += item.tax_amount

            unit_cost = Decimal(item.product.average_cost or 0)
            quantity = Decimal(item.quantity_sold)
            cogs_amount = quantity * unit_cost
            total_cogs += cogs_amount

            warehouse = item.lot.warehouse if item.lot else sale.store.warehouses.filter(
                warehouse_type="store",
                tenant=sale.tenant
            ).first()

            if not warehouse:
                raise ValueError(f"No warehouse found for sale item {item.product.product_name}.")

            InventoryMovement.objects.create(
                tenant=sale.tenant,
                warehouse=warehouse,
                product=item.product,
                product_variant=item.product_variant,
                lot=item.lot,
                sale=sale,
                movement_type="SALE",
                quantity=item.quantity_sold,
                unit_cost=unit_cost,
                total_cost=cogs_amount,
                reference=sale.receipt_number,
                remarks="Sales Posting"
            )

            if item.tax_amount > 0:
                VATLedger.objects.create(
                    tenant=sale.tenant,
                    vat_type="OUTPUT",
                    transaction_reference=sale.receipt_number,
                    taxable_amount=item.subtotal,
                    vat_rate=item.tax_rate_snapshot,
                    vat_amount=item.tax_amount,
                    reporting_period=sale.sale_date.strftime("%Y-%m")
                )

        sale.subtotal = subtotal
        sale.vat_total = vat_total

        # Keep your currency totals from Sale.process_sale().
        # Do not overwrite grand_total blindly unless your app is single-currency.
        if sale.currency in ["USD", "LRD"]:
            sale.recalculate_totals()

        sale.is_posted = True
        sale.status = "POSTED"

        sale.save(update_fields=[
            "subtotal",
            "vat_total",
            "total_usd",
            "total_lrd",
            "grand_total",
            "is_posted",
            "status"
        ])

        JournalService.create_sales_journal(sale)
        JournalService.create_cogs_journal(sale, total_cogs)

        safe_audit_log(
            user=user or sale.cashier,
            tenant=sale.tenant,
            action="SALE_POSTED",
            model_name="Sale",
            object_id=sale.id,
            new_data={
                "receipt_number": sale.receipt_number,
                "subtotal": str(sale.subtotal),
                "vat_total": str(sale.vat_total),
                "grand_total": str(sale.grand_total),
                "total_cogs": str(total_cogs),
            }
        )

        safe_compliance_hook(
            tenant=sale.tenant,
            source="SALE",
            instance=sale
        )

        safe_reconciliation_hook(
            tenant=sale.tenant,
            sale=sale
        )

        return sale