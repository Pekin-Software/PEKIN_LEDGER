from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from taxation.models import (
    VATLedger,
    StoreVATSummary,
    VATReturn,
    VATAdjustment,
    TaxPayment,
)


def prevent_locked_period(tax_period):
    if tax_period.is_locked or tax_period.status in ["FILED", "LOCKED"]:
        raise ValueError("This tax period is locked. No direct VAT changes are allowed.")


def calculate_store_vat_summary(tenant, store, tax_period):
    output_vat = VATLedger.objects.filter(
        tenant=tenant,
        store=store,
        tax_period=tax_period,
        vat_type="OUTPUT",
        is_reversed=False
    ).aggregate(total=Sum("vat_amount"))["total"] or Decimal("0.00")

    input_vat = VATLedger.objects.filter(
        tenant=tenant,
        store=store,
        tax_period=tax_period,
        vat_type="INPUT",
        is_reversed=False
    ).aggregate(total=Sum("vat_amount"))["total"] or Decimal("0.00")

    adjustment_vat = VATLedger.objects.filter(
        tenant=tenant,
        store=store,
        tax_period=tax_period,
        vat_type="ADJUSTMENT",
        is_reversed=False
    ).aggregate(total=Sum("vat_amount"))["total"] or Decimal("0.00")

    net_vat = output_vat - input_vat + adjustment_vat

    summary, _ = StoreVATSummary.objects.update_or_create(
        tenant=tenant,
        store=store,
        tax_period=tax_period,
        defaults={
            "output_vat": output_vat,
            "input_vat": input_vat,
            "adjustment_vat": adjustment_vat,
            "net_vat_payable": net_vat,
        }
    )

    return summary


def submit_store_vat_summary(summary, user):
    prevent_locked_period(summary.tax_period)

    if summary.status not in ["DRAFT", "REJECTED"]:
        raise ValueError("Only draft or rejected summaries can be submitted.")

    summary.status = "SUBMITTED"
    summary.submitted_by = user
    summary.submitted_at = timezone.now()
    summary.rejection_reason = None
    summary.save()

    return summary


def approve_store_vat_summary(summary, user):
    prevent_locked_period(summary.tax_period)

    if summary.status != "SUBMITTED":
        raise ValueError("Only submitted store summaries can be approved.")

    summary.status = "APPROVED"
    summary.reviewed_by = user
    summary.reviewed_at = timezone.now()
    summary.save()

    return summary


def reject_store_vat_summary(summary, user, reason):
    prevent_locked_period(summary.tax_period)

    if summary.status != "SUBMITTED":
        raise ValueError("Only submitted store summaries can be rejected.")

    summary.status = "REJECTED"
    summary.reviewed_by = user
    summary.reviewed_at = timezone.now()
    summary.rejection_reason = reason
    summary.save()

    return summary


def generate_consolidated_vat_return(tenant, tax_period):
    summaries = StoreVATSummary.objects.filter(
        tenant=tenant,
        tax_period=tax_period
    )

    if summaries.exists() and summaries.exclude(status="APPROVED").exists():
        raise ValueError("All store VAT summaries must be approved before consolidation.")

    total_output_vat = summaries.aggregate(total=Sum("output_vat"))["total"] or Decimal("0.00")
    total_input_vat = summaries.aggregate(total=Sum("input_vat"))["total"] or Decimal("0.00")
    total_adjustment_vat = summaries.aggregate(total=Sum("adjustment_vat"))["total"] or Decimal("0.00")

    net_vat = total_output_vat - total_input_vat + total_adjustment_vat

    carried_forward_credit = Decimal("0.00")

    if net_vat < 0:
        carried_forward_credit = abs(net_vat)
        net_vat = Decimal("0.00")

    vat_return, _ = VATReturn.objects.update_or_create(
        tenant=tenant,
        tax_period=tax_period,
        defaults={
            "total_output_vat": total_output_vat,
            "total_input_vat": total_input_vat,
            "total_adjustment_vat": total_adjustment_vat,
            "net_vat_payable": net_vat,
            "carried_forward_credit": carried_forward_credit,
            "status": "DRAFT",
        }
    )

    tax_period.status = "ADMIN_REVIEW"
    tax_period.save()

    return vat_return


def approve_vat_return(vat_return, user):
    if vat_return.status not in ["DRAFT", "UNDER_REVIEW"]:
        raise ValueError("Only draft or under-review VAT returns can be approved.")

    vat_return.status = "APPROVED"
    vat_return.approved_by = user
    vat_return.approved_at = timezone.now()
    vat_return.save()

    vat_return.tax_period.status = "APPROVED"
    vat_return.tax_period.approved_by = user
    vat_return.tax_period.approved_at = timezone.now()
    vat_return.tax_period.save()

    return vat_return


def file_vat_return(vat_return, user, filing_reference):
    if vat_return.status != "APPROVED":
        raise ValueError("Only approved VAT returns can be filed.")

    vat_return.status = "FILED"
    vat_return.filed_by = user
    vat_return.filed_at = timezone.now()
    vat_return.filing_reference = filing_reference
    vat_return.save()

    tax_period = vat_return.tax_period
    tax_period.status = "FILED"
    tax_period.is_locked = True
    tax_period.locked_by = user
    tax_period.locked_at = timezone.now()
    tax_period.save()

    return vat_return


def record_vat_payment(vat_return, user, amount, payment_method, transaction_reference):
    if vat_return.status not in ["FILED", "PAID"]:
        raise ValueError("VAT return must be filed before payment is recorded.")

    payment = TaxPayment.objects.create(
        tenant=vat_return.tenant,
        vat_return=vat_return,
        amount=amount,
        payment_method=payment_method,
        transaction_reference=transaction_reference,
        paid_by=user
    )

    total_paid = vat_return.payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    if total_paid >= vat_return.net_vat_payable:
        vat_return.status = "PAID"
        vat_return.save()

    return payment


@transaction.atomic
def create_vat_adjustment(tenant, store, tax_period, user, adjustment_type, amount, reason):
    prevent_locked_period(tax_period)

    adjustment = VATAdjustment.objects.create(
        tenant=tenant,
        store=store,
        tax_period=tax_period,
        adjustment_type=adjustment_type,
        amount=amount,
        reason=reason,
        created_by=user
    )

    return adjustment


@transaction.atomic
def approve_vat_adjustment(adjustment, user):
    prevent_locked_period(adjustment.tax_period)

    if adjustment.is_approved:
        raise ValueError("This VAT adjustment has already been approved.")

    amount = adjustment.amount

    if adjustment.adjustment_type in ["DECREASE_OUTPUT", "INCREASE_INPUT"]:
        amount = amount * Decimal("-1.00")

    VATLedger.objects.create(
        tenant=adjustment.tenant,
        store=adjustment.store,
        tax_period=adjustment.tax_period,
        vat_type="ADJUSTMENT",
        source_type="MANUAL_ADJUSTMENT",
        transaction_reference=f"VAT-ADJ-{adjustment.id}",
        taxable_amount=Decimal("0.00"),
        vat_rate=Decimal("0.00"),
        vat_amount=amount,
        description=adjustment.reason,
        created_by=user
    )

    adjustment.is_approved = True
    adjustment.approved_by = user
    adjustment.approved_at = timezone.now()
    adjustment.save()

    return adjustment