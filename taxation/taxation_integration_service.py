from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from ledger.models import Account, JournalEntry, JournalLine

from taxation.models import VATLedger

from compliance.models import (
    TaxFiling,
    ComplianceTaxLedger,
    ComplianceAuditLog,
)

from compliance.services import(
    generate_branch_vat_summary, 
    generate_vat_filing, 
    approve_tax_filing,
    submit_tax_filing_to_lra, 
    lock_reporting_period,
)

from reconciliation.models import (
    ReconciliationException,
)


def get_account(tenant, code):
    return Account.objects.get(
        tenant=tenant,
        code=code
    )


@transaction.atomic
def create_output_vat_from_sale(sale, user=None):
    """
    Called after POS sale is posted.
    Creates VAT ledger OUTPUT entry.
    Accounting sales journal is already handled by accounting JournalService.
    """

    if sale.vat_total <= 0:
        return None

    reporting_period = sale.created_at.strftime("%Y-%m")

    ledger = VATLedger.objects.create(
        tenant=sale.tenant,
        store=sale.store,
        vat_type="OUTPUT",
        source_type="SALE",
        transaction_reference=f"SALE-{sale.invoice_number}",
        taxable_amount=sale.subtotal,
        vat_rate=getattr(sale, "vat_rate", Decimal("0.00")),
        vat_amount=sale.vat_total,
        reporting_period=reporting_period,
        tax_type="VATABLE",
        description="Output VAT from POS sale.",
        created_by=user
    )

    ComplianceTaxLedger.objects.create(
        tenant=sale.tenant,
        store=sale.store,
        tax_type="VAT",
        reference=f"SALE-{sale.invoice_number}",
        taxable_amount=sale.subtotal,
        tax_amount=sale.vat_total,
        period_month=reporting_period,
        period_year=sale.created_at.year,
        status="PAYABLE"
    )

    ComplianceAuditLog.objects.create(
        tenant=sale.tenant,
        store=sale.store,
        module="VAT",
        action_type="VAT_EVENT",
        reference=f"SALE-{sale.invoice_number}",
        description="Output VAT ledger created from POS sale.",
        performed_by=user
    )

    return ledger


@transaction.atomic
def create_input_vat_from_purchase(purchase, user=None):
    """
    Called after purchase is finalized.
    Creates VAT ledger INPUT entry.
    Purchase journal is already handled by accounting JournalService.
    """

    if purchase.vat_total <= 0:
        return None

    reporting_period = purchase.created_at.strftime("%Y-%m")

    ledger = VATLedger.objects.create(
        tenant=purchase.tenant,
        store=purchase.store,
        vat_type="INPUT",
        source_type="PURCHASE",
        transaction_reference=f"PUR-{purchase.invoice_number}",
        taxable_amount=purchase.subtotal,
        vat_rate=getattr(purchase, "vat_rate", Decimal("0.00")),
        vat_amount=purchase.vat_total,
        reporting_period=reporting_period,
        tax_type="VATABLE",
        description="Input VAT from supplier purchase.",
        created_by=user
    )

    ComplianceAuditLog.objects.create(
        tenant=purchase.tenant,
        store=purchase.store,
        module="VAT",
        action_type="VAT_EVENT",
        reference=f"PUR-{purchase.invoice_number}",
        description="Input VAT ledger created from supplier purchase.",
        performed_by=user
    )

    return ledger


@transaction.atomic
def prepare_store_vat_for_review(tenant, store, reporting_period, user=None):
    """
    Store manager action.
    Generates branch VAT summary only.
    Store manager does not file VAT.
    """

    summary = generate_branch_vat_summary(
        tenant=tenant,
        store=store,
        reporting_period=reporting_period
    )

    ComplianceAuditLog.objects.create(
        tenant=tenant,
        store=store,
        module="VAT",
        action_type="VAT_FILING_GENERATED",
        reference=f"STORE-VAT-{store.id}-{reporting_period}",
        description="Store VAT summary prepared for admin review.",
        performed_by=user
    )

    return summary


@transaction.atomic
def generate_consolidated_vat_for_admin(tenant, reporting_period, user=None):
    """
    Admin/Finance action.
    Generates tenant-level consolidated VAT filing.
    store=None means consolidated filing.
    """

    filing = generate_vat_filing(
        tenant=tenant,
        reporting_period=reporting_period,
        user=user,
        store=None
    )

    return filing


@transaction.atomic
def approve_consolidated_vat_filing(filing_id, user):
    """
    Admin/Finance approval.
    """

    return approve_tax_filing(
        filing_id=filing_id,
        user=user
    )


@transaction.atomic
def submit_consolidated_vat_to_lra(filing_id, user):
    """
    Admin-only final filing.
    Also posts accounting VAT settlement journal.
    """

    filing = submit_tax_filing_to_lra(
        filing_id=filing_id,
        user=user
    )

    post_vat_filing_journal(filing, user=user)

    lock_reporting_period(
        tenant=filing.tenant,
        store=None,
        reporting_period=filing.reporting_period,
        lock_type="VAT",
        user=user,
        reason="VAT filing submitted and period locked."
    )

    return filing


@transaction.atomic
def post_vat_filing_journal(filing, user=None):
    """
    Accounting integration.
    Clears Output VAT and Input VAT into VAT Payable.
    Uses your ledger chart:
    1300 = Input VAT Receivable
    2100 = Output VAT Payable
    2200 = VAT Payable / Tax Control
    """

    output_vat_account = get_account(filing.tenant, "2100")
    input_vat_account = get_account(filing.tenant, "1300")
    vat_payable_account = get_account(filing.tenant, "2200")

    entry = JournalEntry.objects.create(
        tenant=filing.tenant,
        store=None,
        reference=f"VAT-FILING-{filing.reporting_period}",
        description=f"VAT filing consolidation for {filing.reporting_period}",
        entry_date=timezone.now().date(),
        status="POSTED"
    )

    if filing.output_vat > 0:
        JournalLine.objects.create(
            journal_entry=entry,
            store=None,
            account=output_vat_account,
            description="Clear output VAT payable",
            debit=filing.output_vat,
            credit=Decimal("0.00")
        )

    if filing.input_vat > 0:
        JournalLine.objects.create(
            journal_entry=entry,
            store=None,
            account=input_vat_account,
            description="Clear input VAT receivable",
            debit=Decimal("0.00"),
            credit=filing.input_vat
        )

    if filing.net_tax_payable > 0:
        JournalLine.objects.create(
            journal_entry=entry,
            store=None,
            account=vat_payable_account,
            description="Net VAT payable to LRA",
            debit=Decimal("0.00"),
            credit=filing.net_tax_payable
        )

    return entry


@transaction.atomic
def post_vat_payment_journal(filing, amount, payment_reference, bank_account_code="1000"):
    """
    Accounting integration after VAT payment.
    """

    vat_payable_account = get_account(filing.tenant, "2200")
    bank_account = get_account(filing.tenant, bank_account_code)

    entry = JournalEntry.objects.create(
        tenant=filing.tenant,
        store=None,
        reference=f"VAT-PAYMENT-{payment_reference}",
        description=f"VAT payment for {filing.reporting_period}",
        entry_date=timezone.now().date(),
        status="POSTED"
    )

    JournalLine.objects.create(
        journal_entry=entry,
        store=None,
        account=vat_payable_account,
        description="Reduce VAT payable",
        debit=amount,
        credit=Decimal("0.00")
    )

    JournalLine.objects.create(
        journal_entry=entry,
        store=None,
        account=bank_account,
        description="VAT payment from bank/cash account",
        debit=Decimal("0.00"),
        credit=amount
    )

    filing.status = "PAID"
    filing.save(update_fields=["status"])

    ComplianceTaxLedger.objects.filter(
        tenant=filing.tenant,
        tax_type="VAT",
        period_month=filing.reporting_period
    ).update(status="PAID")

    ComplianceAuditLog.objects.create(
        tenant=filing.tenant,
        store=None,
        module="VAT",
        action_type="TAX_FILING_SUBMITTED",
        reference=f"VAT-PAYMENT-{payment_reference}",
        description="VAT payment journal posted and filing marked as paid.",
    )

    return entry


def raise_vat_reconciliation_exception(
    tenant,
    store,
    reference,
    expected_amount,
    actual_amount,
):
    variance = actual_amount - expected_amount

    if variance == Decimal("0.00"):
        return None

    return ReconciliationException.objects.create(
        tenant=tenant,
        store=store,
        exception_type="VAT_VARIANCE",
        reference=reference,
        expected_amount=expected_amount,
        actual_amount=actual_amount,
        variance=variance
    )