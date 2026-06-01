from django.db import transaction
from accounting.services.journal_services import JournalService


from taxation.taxation_integration_service import (
    create_output_vat_from_sale,
    create_input_vat_from_purchase,
)

from reconciliation.services.services import (
    create_supplier_vat_transaction,
    reconcile_supplier_vat_transaction,
)


@transaction.atomic
def post_sale_with_tax_and_compliance(sale, user=None, cogs_amount=None):
    """
    Full sale posting flow:
    1. Accounting sales journal
    2. Optional COGS journal
    3. Output VAT ledger
    4. Compliance tax ledger/audit log
    """

    sales_journal_id = JournalService.create_sales_journal(sale)

    cogs_journal_id = None
    if cogs_amount is not None:
        cogs_journal_id = JournalService.create_cogs_journal(
            sale=sale,
            cogs_amount=cogs_amount
        )

    vat_ledger = create_output_vat_from_sale(
        sale=sale,
        user=user
    )

    return {
        "sales_journal_id": sales_journal_id,
        "cogs_journal_id": cogs_journal_id,
        "vat_ledger_id": vat_ledger.id if vat_ledger else None,
    }


@transaction.atomic
def post_purchase_with_tax_and_reconciliation(purchase, user=None):
    """
    Full purchase posting flow:
    1. Accounting purchase journal
    2. Input VAT ledger
    3. Supplier VAT transaction
    4. Supplier VAT reconciliation
    """

    purchase_journal_id = JournalService.create_purchase_journal(purchase)

    vat_ledger = create_input_vat_from_purchase(
        purchase=purchase,
        user=user
    )

    supplier_vat_transaction = None
    supplier_vat_reconciliation = None

    if purchase.vat_total > 0:
        supplier_vat_transaction = create_supplier_vat_transaction(
            purchase_id=purchase.id,
            supplier_vat_amount=purchase.vat_total,
            tenant=purchase.tenant,
            store=purchase.store
        )

        supplier_vat_reconciliation = reconcile_supplier_vat_transaction(
            supplier_vat_transaction_id=supplier_vat_transaction.id,
            user=user,
            tenant=purchase.tenant,
            store=purchase.store
        )

    return {
        "purchase_journal_id": purchase_journal_id,
        "vat_ledger_id": vat_ledger.id if vat_ledger else None,
        "supplier_vat_transaction_id": supplier_vat_transaction.id if supplier_vat_transaction else None,
        "supplier_vat_reconciliation_id": supplier_vat_reconciliation.id if supplier_vat_reconciliation else None,
    }