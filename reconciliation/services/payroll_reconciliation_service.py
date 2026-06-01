from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from reconciliation.models import (
    CashTransaction,
    MobileMoneyTransaction,
    PayrollPaymentReconciliation,
    PAYEPaymentReconciliation
)


def get_reconciliation_status(expected, actual):

    variance = actual - expected

    if variance == Decimal('0.00'):
        return 'MATCHED', variance

    if actual < expected:
        return 'PARTIAL', variance

    return 'MISMATCH', variance


@transaction.atomic
def reconcile_payroll_salary_payment(
    payroll_run,
    payment_method,
    transaction_reference,
    reconciled_by
):

    expected_amount = payroll_run.total_net_salary

    if payment_method == 'CASH':
        transaction_obj = CashTransaction.objects.select_for_update().get(
            tenant=payroll_run.tenant,
            store=payroll_run.store,
            transaction_reference=transaction_reference,
            transaction_type='PAYROLL_PAYMENT',
            is_reconciled=False
        )

        actual_amount = transaction_obj.amount

        status, variance = get_reconciliation_status(
            expected_amount,
            actual_amount
        )

        reconciliation = PayrollPaymentReconciliation.objects.create(
            tenant=payroll_run.tenant,
            store=payroll_run.store,
            payroll_run=payroll_run,
            payment_method='CASH',
            cash_transaction=transaction_obj,
            expected_amount=expected_amount,
            actual_amount=actual_amount,
            variance_amount=variance,
            status=status,
            reconciled_by=reconciled_by
        )

        transaction_obj.is_reconciled = True
        transaction_obj.save()

        return reconciliation

    if payment_method == 'MOBILE_MONEY':
        transaction_obj = MobileMoneyTransaction.objects.select_for_update().get(
            tenant=payroll_run.tenant,
            store=payroll_run.store,
            transaction_reference=transaction_reference,
            transaction_type='PAYROLL_PAYMENT',
            is_reconciled=False
        )

        actual_amount = transaction_obj.amount

        status, variance = get_reconciliation_status(
            expected_amount,
            actual_amount
        )

        reconciliation = PayrollPaymentReconciliation.objects.create(
            tenant=payroll_run.tenant,
            store=payroll_run.store,
            payroll_run=payroll_run,
            payment_method='MOBILE_MONEY',
            mobile_money_transaction=transaction_obj,
            expected_amount=expected_amount,
            actual_amount=actual_amount,
            variance_amount=variance,
            status=status,
            reconciled_by=reconciled_by
        )

        transaction_obj.is_reconciled = True
        transaction_obj.reconciled_at = timezone.now()
        transaction_obj.reconciled_by = reconciled_by
        transaction_obj.matched_amount = actual_amount
        transaction_obj.remaining_amount = Decimal('0.00')
        transaction_obj.is_partial_match = status == 'PARTIAL'
        transaction_obj.save()

        return reconciliation

    raise ValueError('Invalid payment method.')


@transaction.atomic
def reconcile_paye_payment(
    compliance_tax,
    payment_method,
    transaction_reference,
    reconciled_by
):

    expected_amount = compliance_tax.tax_amount

    if payment_method == 'CASH':
        transaction_obj = CashTransaction.objects.select_for_update().get(
            tenant=compliance_tax.tenant,
            store=compliance_tax.store,
            transaction_reference=transaction_reference,
            transaction_type='PAYE_PAYMENT',
            is_reconciled=False
        )

        actual_amount = transaction_obj.amount

        status, variance = get_reconciliation_status(
            expected_amount,
            actual_amount
        )

        reconciliation = PAYEPaymentReconciliation.objects.create(
            tenant=compliance_tax.tenant,
            store=compliance_tax.store,
            compliance_tax=compliance_tax,
            payment_method='CASH',
            cash_transaction=transaction_obj,
            expected_amount=expected_amount,
            actual_amount=actual_amount,
            variance_amount=variance,
            status=status,
            reconciled_by=reconciled_by
        )

        transaction_obj.is_reconciled = True
        transaction_obj.save()

    elif payment_method == 'MOBILE_MONEY':
        transaction_obj = MobileMoneyTransaction.objects.select_for_update().get(
            tenant=compliance_tax.tenant,
            store=compliance_tax.store,
            transaction_reference=transaction_reference,
            transaction_type='PAYE_PAYMENT',
            is_reconciled=False
        )

        actual_amount = transaction_obj.amount

        status, variance = get_reconciliation_status(
            expected_amount,
            actual_amount
        )

        reconciliation = PAYEPaymentReconciliation.objects.create(
            tenant=compliance_tax.tenant,
            store=compliance_tax.store,
            compliance_tax=compliance_tax,
            payment_method='MOBILE_MONEY',
            mobile_money_transaction=transaction_obj,
            expected_amount=expected_amount,
            actual_amount=actual_amount,
            variance_amount=variance,
            status=status,
            reconciled_by=reconciled_by
        )

        transaction_obj.is_reconciled = True
        transaction_obj.reconciled_at = timezone.now()
        transaction_obj.reconciled_by = reconciled_by
        transaction_obj.matched_amount = actual_amount
        transaction_obj.remaining_amount = Decimal('0.00')
        transaction_obj.is_partial_match = status == 'PARTIAL'
        transaction_obj.save()

    else:
        raise ValueError('Invalid payment method.')

    if status == 'MATCHED':
        compliance_tax.status = 'PAID'
        compliance_tax.save()

    return reconciliation