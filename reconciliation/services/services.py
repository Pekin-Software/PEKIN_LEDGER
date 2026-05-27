from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.shortcuts import get_object_or_404

from sales.models import Sale
from inventory.models import Purchase

from ..models import (
    CashTransaction,
    CashReconciliation,
    MobileMoneyTransaction,
    MobileMoneyReconciliation,
    SupplierVATTransaction,
    SupplierVATReconciliation,
    ReconciliationException
)


@transaction.atomic
def reconcile_cash(
    tenant,
    store,
    user,
    counted_cash,
    opening_cash=Decimal("0.00"),
    cashier=None,
    shift_reference=None,
    start_date=None,
    end_date=None,
):
    cash_queryset = CashTransaction.objects.select_for_update().filter(
        tenant=tenant,
        store=store,
        is_reconciled=False,
    )

    if cashier:
        cash_queryset = cash_queryset.filter(
            cashier=cashier
        )

    if start_date and end_date:
        cash_queryset = cash_queryset.filter(
            transaction_date__range=[
                start_date,
                end_date,
            ]
        )

    system_cash_sales = (
        cash_queryset.aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")
    )

    expected_cash = opening_cash + system_cash_sales
    variance = counted_cash - expected_cash

    if variance == Decimal("0.00"):
        status = "MATCHED"
    elif variance < Decimal("0.00"):
        status = "SHORTAGE"
    else:
        status = "OVERAGE"

    reconciliation = CashReconciliation.objects.create(
        tenant=tenant,
        store=store,
        cashier=cashier,
        opening_cash=opening_cash,
        system_cash_sales=system_cash_sales,
        counted_cash=counted_cash,
        variance=variance,
        status=status,
        shift_reference=shift_reference,
        reconciled_by=user,
    )

    cash_queryset.update(
        is_reconciled=True,
        cash_reconciliation=reconciliation,
    )

    if status in ["SHORTAGE", "OVERAGE"]:
        ReconciliationException.objects.create(
            tenant=tenant,
            store=store,
            exception_type=(
                "CASH_SHORTAGE"
                if status == "SHORTAGE"
                else "CASH_OVERAGE"
            ),
            reference=shift_reference or f"CASH-{reconciliation.id}",
            expected_amount=expected_cash,
            actual_amount=counted_cash,
            variance=variance,
        )

    return reconciliation


@transaction.atomic
def reconcile_mobile_money_transaction(
    momo_transaction_id,
    sale_id,
    user,
    tenant,
    store,
):
    momo = get_object_or_404(
        MobileMoneyTransaction.objects.select_for_update(),
        id=momo_transaction_id,
        tenant=tenant,
        store=store,
    )

    if momo.is_reconciled:
        raise ValueError("MoMo transaction already reconciled.")

    sale = get_object_or_404(
        Sale,
        id=sale_id,
        tenant=tenant,
        store=store,
    )

    expected_amount = sale.grand_total
    actual_amount = momo.amount
    variance = actual_amount - expected_amount

    status = "MATCHED" if variance == Decimal("0.00") else "MISMATCH"

    reconciliation = MobileMoneyReconciliation.objects.create(
        tenant=tenant,
        store=store,
        momo_transaction=momo,
        sale=sale,
        expected_amount=expected_amount,
        actual_amount=actual_amount,
        variance_amount=variance,
        status=status,
        reconciled_by=user,
    )

    if status == "MATCHED":
        momo.is_reconciled = True
        momo.sale = sale
        momo.matched_amount = actual_amount
        momo.remaining_amount = Decimal("0.00")
        momo.is_partial_match = False
        momo.reconciled_at = timezone.now()
        momo.reconciled_by = user
        momo.save()
    else:
        ReconciliationException.objects.create(
            tenant=tenant,
            store=store,
            exception_type="MOMO_MISMATCH",
            reference=momo.transaction_reference,
            expected_amount=expected_amount,
            actual_amount=actual_amount,
            variance=variance,
        )

    return reconciliation


@transaction.atomic
def create_supplier_vat_transaction(
    purchase_id,
    supplier_vat_amount,
    tenant,
    store,
):
    purchase = get_object_or_404(
        Purchase,
        id=purchase_id,
        tenant=tenant,
        store=store,
    )

    transaction = SupplierVATTransaction.objects.create(
        tenant=tenant,
        store=store,
        supplier=purchase.supplier,
        purchase=purchase,
        supplier_invoice_number=purchase.invoice_number,
        supplier_vat_amount=supplier_vat_amount,
    )

    return transaction


@transaction.atomic
def reconcile_supplier_vat_transaction(
    supplier_vat_transaction_id,
    user,
    tenant,
    store,
):
    supplier_vat_transaction = get_object_or_404(
        SupplierVATTransaction.objects.select_for_update(),
        id=supplier_vat_transaction_id,
        tenant=tenant,
        store=store,
    )

    purchase = supplier_vat_transaction.purchase

    expected_vat_amount = purchase.vat_total
    actual_vat_amount = supplier_vat_transaction.supplier_vat_amount
    variance = actual_vat_amount - expected_vat_amount

    status = "MATCHED" if variance == Decimal("0.00") else "MISMATCH"

    reconciliation = SupplierVATReconciliation.objects.create(
        tenant=tenant,
        store=store,
        supplier_vat_transaction=supplier_vat_transaction,
        purchase=purchase,
        expected_vat_amount=expected_vat_amount,
        actual_vat_amount=actual_vat_amount,
        variance_amount=variance,
        status=status,
        reconciled_by=user,
    )

    supplier_vat_transaction.is_reconciled = True
    supplier_vat_transaction.save()

    if status == "MISMATCH":
        ReconciliationException.objects.create(
            tenant=tenant,
            store=store,
            exception_type="VAT_VARIANCE",
            reference=supplier_vat_transaction.supplier_invoice_number,
            expected_amount=expected_vat_amount,
            actual_amount=actual_vat_amount,
            variance=variance,
        )

    return reconciliation