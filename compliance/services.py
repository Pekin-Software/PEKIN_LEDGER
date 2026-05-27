import hashlib
import json
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from sales.models import Sale
from taxation.models import VATLedger

from compliance.models import (
    EInvoice,
    EInvoiceLine,
    TaxFiling,
    PeriodLock,
    ComplianceAuditLog,
    POSComplianceEvent,
    InventoryComplianceEvent,
    BranchVATSummary,
)


def get_sale_tenant(sale):
    return getattr(sale, "tenant", None) or getattr(sale, "business_name", None)


def get_sale_store(sale):
    return getattr(sale, "store", None) or getattr(sale, "store_name", None) or getattr(sale, "branch", None)


def create_audit_log(
    tenant,
    action_type,
    reference,
    user=None,
    description=None,
    store=None,
    module="COMPLIANCE",
):
    return ComplianceAuditLog.objects.create(
        tenant=tenant,
        store=store,
        module=module,
        action_type=action_type,
        reference=reference,
        description=description,
        performed_by=user,
    )


def generate_invoice_signature(payload):
    raw_payload = json.dumps(payload, sort_keys=True, default=str)

    return hashlib.sha256(
        raw_payload.encode("utf-8")
    ).hexdigest()


def build_invoice_payload(invoice):
    tenant_name = getattr(invoice.tenant, "name", None) or str(invoice.tenant)
    tenant_tin = getattr(invoice.tenant, "tin", None)

    return {
        "invoice_number": invoice.invoice_number,
        "tenant": tenant_name,
        "tin": tenant_tin,
        "store": str(invoice.store),
        "subtotal": str(invoice.subtotal),
        "vat_total": str(invoice.vat_total),
        "grand_total": str(invoice.grand_total),
        "issued_at": str(invoice.issued_at),
    }


@transaction.atomic
def create_e_invoice_from_sale(sale_id, user=None):
    sale = Sale.objects.select_for_update().get(id=sale_id)

    tenant = get_sale_tenant(sale)
    store = get_sale_store(sale)

    if tenant is None:
        raise ValueError("Sale does not have a tenant.")

    if store is None:
        raise ValueError("Sale does not have a store/branch.")

    invoice_number = getattr(sale, "invoice_number", None) or getattr(sale, "sale_number", None)

    if not invoice_number:
        raise ValueError("Sale does not have an invoice number or sale number.")

    existing_invoice = EInvoice.objects.filter(
        tenant=tenant,
        store=store,
        invoice_number=invoice_number,
    ).first()

    if existing_invoice:
        return existing_invoice

    invoice = EInvoice.objects.create(
        tenant=tenant,
        store=store,
        invoice_number=invoice_number,
        customer_name=getattr(sale, "customer_name", None) or "Walk-in Customer",
        customer_tin=getattr(sale, "customer_tin", None),
        subtotal=sale.subtotal,
        vat_total=sale.vat_total,
        grand_total=sale.grand_total,
        created_by=user,
        status="DRAFT",
    )

    for item in sale.items.all():
        product = getattr(item, "product", None)

        EInvoiceLine.objects.create(
            invoice=invoice,
            description=getattr(item, "product_name", None) or str(product),
            quantity=item.quantity,
            unit_price=item.unit_price,
            taxable_amount=getattr(item, "subtotal", Decimal("0.00")),
            vat_rate=getattr(item, "tax_rate_snapshot", Decimal("0.00")),
            vat_amount=getattr(item, "tax_amount", Decimal("0.00")),
            line_total=getattr(item, "total", Decimal("0.00")),
            tax_type=getattr(getattr(item, "tax_class", None), "tax_type", "VATABLE"),
        )

    invoice.issue()

    payload = build_invoice_payload(invoice)
    signature = generate_invoice_signature(payload)

    tenant_tin = getattr(invoice.tenant, "tin", None)

    invoice.digital_signature = signature
    invoice.qr_code_payload = json.dumps({
        "invoice_number": invoice.invoice_number,
        "tin": tenant_tin,
        "store": str(invoice.store),
        "grand_total": str(invoice.grand_total),
        "vat_total": str(invoice.vat_total),
        "signature": signature,
    })

    invoice.save(update_fields=["digital_signature", "qr_code_payload"])

    POSComplianceEvent.objects.create(
        tenant=tenant,
        store=store,
        sale_reference=invoice.invoice_number,
        event_type="EINVOICE_ISSUED",
        cashier=user,
        amount=invoice.grand_total,
        vat_amount=invoice.vat_total,
        is_compliant=True,
        note="E-invoice issued from POS sale.",
    )

    create_audit_log(
        tenant=tenant,
        store=store,
        module="POS",
        action_type="EINVOICE_CREATED",
        reference=invoice.invoice_number,
        user=user,
        description="E-invoice created from sale.",
    )

    return invoice


def verify_invoice_signature(invoice_id, user=None):
    invoice = EInvoice.objects.get(id=invoice_id)

    payload = build_invoice_payload(invoice)
    expected_signature = generate_invoice_signature(payload)
    is_valid = invoice.digital_signature == expected_signature

    create_audit_log(
        tenant=invoice.tenant,
        store=invoice.store,
        module="COMPLIANCE",
        action_type="EINVOICE_VERIFIED",
        reference=invoice.invoice_number,
        user=user,
        description="Invoice verification passed." if is_valid else "Invoice verification failed.",
    )

    return {
        "invoice_number": invoice.invoice_number,
        "is_valid": is_valid,
        "stored_signature": invoice.digital_signature,
        "expected_signature": expected_signature,
    }


def is_period_locked(
    tenant,
    reporting_period,
    lock_type="FULL",
    store=None,
):
    tenant_level_locked = PeriodLock.objects.filter(
        tenant=tenant,
        store__isnull=True,
        reporting_period=reporting_period,
        lock_type__in=[lock_type, "FULL"],
        is_locked=True,
    ).exists()

    if tenant_level_locked:
        return True

    if store:
        return PeriodLock.objects.filter(
            tenant=tenant,
            store=store,
            reporting_period=reporting_period,
            lock_type__in=[lock_type, "FULL"],
            is_locked=True,
        ).exists()

    return False


@transaction.atomic
def generate_branch_vat_summary(
    tenant,
    reporting_period,
    store,
):
    vat_entries = VATLedger.objects.filter(
        tenant=tenant,
        store=store,
        reporting_period=reporting_period,
    )

    output_vat = Decimal("0.00")
    input_vat = Decimal("0.00")
    taxable_sales = Decimal("0.00")
    exempt_sales = Decimal("0.00")
    zero_rated_sales = Decimal("0.00")

    for entry in vat_entries:
        tax_type = getattr(entry, "tax_type", None)

        if getattr(entry, "vat_type", None) == "OUTPUT":
            if tax_type == "EXEMPT":
                exempt_sales += entry.taxable_amount
            elif tax_type == "ZERO_RATED":
                zero_rated_sales += entry.taxable_amount
            else:
                taxable_sales += entry.taxable_amount

            output_vat += entry.vat_amount

        elif getattr(entry, "vat_type", None) == "INPUT":
            input_vat += entry.vat_amount

    net_vat = output_vat - input_vat

    summary, created = BranchVATSummary.objects.update_or_create(
        tenant=tenant,
        store=store,
        reporting_period=reporting_period,
        defaults={
            "taxable_sales": taxable_sales,
            "exempt_sales": exempt_sales,
            "zero_rated_sales": zero_rated_sales,
            "output_vat": output_vat,
            "input_vat": input_vat,
            "net_vat": net_vat,
        },
    )

    return summary


@transaction.atomic
def generate_vat_filing(
    tenant,
    reporting_period,
    user=None,
    store=None,
):
    if is_period_locked(
        tenant=tenant,
        store=store,
        reporting_period=reporting_period,
        lock_type="VAT",
    ):
        raise ValueError("VAT reporting period is locked.")

    vat_entries = VATLedger.objects.filter(
        tenant=tenant,
        reporting_period=reporting_period,
    )

    if store:
        vat_entries = vat_entries.filter(store=store)

    output_vat = Decimal("0.00")
    input_vat = Decimal("0.00")
    taxable_sales = Decimal("0.00")
    exempt_sales = Decimal("0.00")

    for entry in vat_entries:
        tax_type = getattr(entry, "tax_type", None)

        if getattr(entry, "vat_type", None) == "OUTPUT":
            if tax_type == "EXEMPT":
                exempt_sales += entry.taxable_amount
            else:
                taxable_sales += entry.taxable_amount

            output_vat += entry.vat_amount

        elif getattr(entry, "vat_type", None) == "INPUT":
            input_vat += entry.vat_amount

    net_tax = output_vat - input_vat

    filing, created = TaxFiling.objects.update_or_create(
        tenant=tenant,
        store=store,
        tax_type="VAT",
        reporting_period=reporting_period,
        defaults={
            "total_taxable_sales": taxable_sales,
            "total_exempt_sales": exempt_sales,
            "output_vat": output_vat,
            "input_vat": input_vat,
            "net_tax_payable": net_tax,
            "status": "READY_FOR_REVIEW",
        },
    )

    create_audit_log(
        tenant=tenant,
        store=store,
        module="VAT",
        action_type="VAT_FILING_GENERATED",
        reference=f"VAT-{reporting_period}",
        user=user,
        description="VAT filing generated from VAT ledger.",
    )

    return filing


@transaction.atomic
def approve_tax_filing(filing_id, user):
    filing = TaxFiling.objects.select_for_update().get(id=filing_id)

    if filing.status != "READY_FOR_REVIEW":
        raise ValueError("Only filings ready for review can be approved.")

    filing.status = "APPROVED"
    filing.approved_by = user
    filing.approved_at = timezone.now()

    filing.save(update_fields=["status", "approved_by", "approved_at"])

    create_audit_log(
        tenant=filing.tenant,
        store=filing.store,
        module="VAT",
        action_type="TAX_FILING_APPROVED",
        reference=f"{filing.tax_type}-{filing.reporting_period}",
        user=user,
        description="Tax filing approved.",
    )

    return filing


@transaction.atomic
def submit_tax_filing_to_lra(filing_id, user=None):
    filing = TaxFiling.objects.select_for_update().get(id=filing_id)

    if filing.status != "APPROVED":
        raise ValueError("Only approved filings can be submitted.")

    simulated_lra_reference = (
        f"LRA-{filing.tax_type}-"
        f"{filing.reporting_period}-"
        f"{filing.id}"
    )

    filing.lra_reference = simulated_lra_reference
    filing.submitted_at = timezone.now()
    filing.status = "SUBMITTED"

    filing.save(update_fields=["lra_reference", "submitted_at", "status"])

    create_audit_log(
        tenant=filing.tenant,
        store=filing.store,
        module="VAT",
        action_type="TAX_FILING_SUBMITTED",
        reference=simulated_lra_reference,
        user=user,
        description="Tax filing submitted to simulated LRA endpoint.",
    )

    return filing


@transaction.atomic
def lock_reporting_period(
    tenant,
    reporting_period,
    lock_type,
    user=None,
    reason=None,
    store=None,
):
    period_lock, created = PeriodLock.objects.get_or_create(
        tenant=tenant,
        store=store,
        reporting_period=reporting_period,
        lock_type=lock_type,
    )

    if period_lock.is_locked:
        return period_lock

    period_lock.lock(user=user, reason=reason)

    create_audit_log(
        tenant=tenant,
        store=store,
        module="COMPLIANCE",
        action_type="PERIOD_LOCKED",
        reference=f"{reporting_period}-{lock_type}",
        user=user,
        description=reason or "Reporting period locked.",
    )

    return period_lock


def record_pos_compliance_event(
    tenant,
    store,
    sale_reference,
    event_type,
    cashier=None,
    amount=Decimal("0.00"),
    vat_amount=Decimal("0.00"),
    is_compliant=True,
    note=None,
):
    event = POSComplianceEvent.objects.create(
        tenant=tenant,
        store=store,
        sale_reference=sale_reference,
        event_type=event_type,
        cashier=cashier,
        amount=amount,
        vat_amount=vat_amount,
        is_compliant=is_compliant,
        note=note,
    )

    create_audit_log(
        tenant=tenant,
        store=store,
        module="POS",
        action_type="POS_EVENT",
        reference=sale_reference,
        user=cashier,
        description=note,
    )

    return event

@transaction.atomic
def generate_branch_vat_summary(
    tenant,
    reporting_period,
    store
):
    vat_entries = VATLedger.objects.filter(
        tenant=tenant,
        store=store,
        reporting_period=reporting_period
    )

    taxable_sales = Decimal("0.00")
    exempt_sales = Decimal("0.00")
    zero_rated_sales = Decimal("0.00")
    output_vat = Decimal("0.00")
    input_vat = Decimal("0.00")

    for entry in vat_entries:
        if entry.vat_type == "OUTPUT":
            if entry.tax_type == "EXEMPT":
                exempt_sales += entry.taxable_amount
            elif entry.tax_type == "ZERO_RATED":
                zero_rated_sales += entry.taxable_amount
            else:
                taxable_sales += entry.taxable_amount

            output_vat += entry.vat_amount

        elif entry.vat_type == "INPUT":
            input_vat += entry.vat_amount

    net_vat = output_vat - input_vat

    summary, created = BranchVATSummary.objects.update_or_create(
        tenant=tenant,
        store=store,
        reporting_period=reporting_period,
        defaults={
            "taxable_sales": taxable_sales,
            "exempt_sales": exempt_sales,
            "zero_rated_sales": zero_rated_sales,
            "output_vat": output_vat,
            "input_vat": input_vat,
            "net_vat": net_vat,
        }
    )

    return summary

def record_inventory_compliance_event(
    tenant,
    reference,
    event_type,
    store=None,
    destination_store=None,
    product_name=None,
    quantity=Decimal("0.00"),
    is_compliant=True,
    note=None,
    user=None,
):
    event = InventoryComplianceEvent.objects.create(
        tenant=tenant,
        store=store,
        destination_store=destination_store,
        reference=reference,
        event_type=event_type,
        product_name=product_name,
        quantity=quantity,
        is_compliant=is_compliant,
        note=note,
        performed_by=user,
    )

    create_audit_log(
        tenant=tenant,
        store=store,
        module="INVENTORY",
        action_type="INVENTORY_EVENT",
        reference=reference,
        user=user,
        description=note,
    )

    return event