from django.db import transaction
from django.utils import timezone

from compliance.models import ComplianceTaxLedger

from reconciliation.models import (
    CashTransaction,
    MobileMoneyTransaction
)

from reconciliation.services.payroll_reconciliation_service import (
    reconcile_payroll_salary_payment,
    reconcile_paye_payment
)


def create_cash_transaction(
    tenant,
    store,
    transaction_type,
    amount,
    transaction_reference,
    user
):
    return CashTransaction.objects.create(
        tenant=tenant,
        store=store,
        transaction_type=transaction_type,
        sale=None,
        cashier=user,
        amount=amount,
        transaction_reference=transaction_reference
    )


def create_mobile_money_transaction(
    tenant,
    store,
    transaction_type,
    amount,
    transaction_reference,
    provider
):
    return MobileMoneyTransaction.objects.create(
        tenant=tenant,
        store=store,
        provider=provider,
        transaction_type=transaction_type,
        transaction_reference=transaction_reference,
        amount=amount,
        transaction_date=timezone.now(),
        sale=None
    )


@transaction.atomic
def complete_full_payroll_payment(
    payroll_run,
    salary_payment_method,
    salary_transaction_reference,
    paye_payment_method,
    paye_transaction_reference,
    paid_by,
    salary_provider=None,
    paye_provider=None
):

    if payroll_run.status != 'POSTED':
        raise ValueError('Only POSTED payroll can be paid.')

    compliance_tax = ComplianceTaxLedger.objects.select_for_update().get(
        tenant=payroll_run.tenant,
        store=payroll_run.store,
        tax_type='PAYE',
        reference=f'PAYROLL-{payroll_run.id}',
        status='PAYABLE'
    )

    salary_amount = payroll_run.total_net_salary
    paye_amount = compliance_tax.tax_amount

    if salary_payment_method == 'CASH':
        create_cash_transaction(
            tenant=payroll_run.tenant,
            store=payroll_run.store,
            transaction_type='PAYROLL_PAYMENT',
            amount=salary_amount,
            transaction_reference=salary_transaction_reference,
            user=paid_by
        )

    elif salary_payment_method == 'MOBILE_MONEY':
        if not salary_provider:
            raise ValueError('Salary provider is required for mobile money.')

        create_mobile_money_transaction(
            tenant=payroll_run.tenant,
            store=payroll_run.store,
            transaction_type='PAYROLL_PAYMENT',
            amount=salary_amount,
            transaction_reference=salary_transaction_reference,
            provider=salary_provider
        )

    else:
        raise ValueError('Invalid salary payment method.')

    salary_reconciliation = reconcile_payroll_salary_payment(
        payroll_run=payroll_run,
        payment_method=salary_payment_method,
        transaction_reference=salary_transaction_reference,
        reconciled_by=paid_by
    )

    if paye_payment_method == 'CASH':
        create_cash_transaction(
            tenant=payroll_run.tenant,
            store=payroll_run.store,
            transaction_type='PAYE_PAYMENT',
            amount=paye_amount,
            transaction_reference=paye_transaction_reference,
            user=paid_by
        )

    elif paye_payment_method == 'MOBILE_MONEY':
        if not paye_provider:
            raise ValueError('PAYE provider is required for mobile money.')

        create_mobile_money_transaction(
            tenant=payroll_run.tenant,
            store=payroll_run.store,
            transaction_type='PAYE_PAYMENT',
            amount=paye_amount,
            transaction_reference=paye_transaction_reference,
            provider=paye_provider
        )

    else:
        raise ValueError('Invalid PAYE payment method.')

    paye_reconciliation = reconcile_paye_payment(
        compliance_tax=compliance_tax,
        payment_method=paye_payment_method,
        transaction_reference=paye_transaction_reference,
        reconciled_by=paid_by
    )

    return {
        'salary_reconciliation': salary_reconciliation,
        'paye_reconciliation': paye_reconciliation,
        'compliance_tax': compliance_tax
    }