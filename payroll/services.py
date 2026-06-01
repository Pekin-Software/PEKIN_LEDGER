from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from audit.models import AuditLog
from compliance.models import ComplianceTaxLedger
from .models import (
    PAYETaxBracket,
    PayrollRun,
    PayrollItem,
    Employee
)

from ledger.models import (
    JournalEntry,
    JournalLine,
    Account
)

from stores.models import StoreUserAssignment


def calculate_paye(gross_salary, tenant):

    brackets = PAYETaxBracket.objects.filter(
        tenant=tenant,
        is_active=True
    ).order_by('min_income')

    paye = Decimal('0.00')

    for bracket in brackets:
        if bracket.min_income <= gross_salary <= bracket.max_income:
            paye = (gross_salary * bracket.rate) / Decimal('100')
            break

    return paye


@transaction.atomic
def generate_payroll_items(payroll_run_id):

    payroll_run = PayrollRun.objects.select_for_update().get(
        id=payroll_run_id
    )

    if payroll_run.status not in ['DRAFT', 'REJECTED']:
        raise ValueError(
            'Payroll items can only be generated when payroll is in DRAFT or REJECTED status.'
        )

    PayrollItem.objects.filter(
        payroll_run=payroll_run
    ).delete()

    active_assignment_user_ids = StoreUserAssignment.objects.filter(
        store=payroll_run.store,
        is_active=True
    ).values_list('user_id', flat=True)

    employees = Employee.objects.filter(
        user__tenant=payroll_run.tenant,
        user_id__in=active_assignment_user_ids,
        employment_status='ACTIVE'
    ).select_related('user')

    total_gross = Decimal('0.00')
    total_paye = Decimal('0.00')
    total_net = Decimal('0.00')

    for employee in employees:

        gross_salary = employee.base_salary

        paye = calculate_paye(
            gross_salary=gross_salary,
            tenant=payroll_run.tenant
        )

        withholding = Decimal('0.00')
        deductions = paye + withholding
        net_salary = gross_salary - deductions

        PayrollItem.objects.create(
            payroll_run=payroll_run,
            employee=employee,
            gross_salary=gross_salary,
            paye_amount=paye,
            withholding_tax=withholding,
            deductions=deductions,
            net_salary=net_salary
        )

        total_gross += gross_salary
        total_paye += paye
        total_net += net_salary

    payroll_run.total_gross_salary = total_gross
    payroll_run.total_paye = total_paye
    payroll_run.total_net_salary = total_net
    payroll_run.status = 'DRAFT'
    payroll_run.save()

    return payroll_run


@transaction.atomic
def submit_payroll(payroll_run_id):

    payroll_run = PayrollRun.objects.select_for_update().get(
        id=payroll_run_id
    )

    if payroll_run.status != 'DRAFT':
        raise ValueError('Only DRAFT payroll can be submitted.')

    if not payroll_run.items.exists():
        raise ValueError('Payroll cannot be submitted without payroll items.')

    payroll_run.status = 'SUBMITTED'
    payroll_run.save()

    return payroll_run


@transaction.atomic
def approve_payroll(payroll_run_id, admin_user):

    payroll_run = PayrollRun.objects.select_for_update().get(
        id=payroll_run_id
    )

    if payroll_run.status != 'SUBMITTED':
        raise ValueError('Only SUBMITTED payroll can be approved.')

    payroll_run.status = 'APPROVED'
    payroll_run.approved_by = admin_user
    payroll_run.approved_at = timezone.now()
    payroll_run.save()

    return payroll_run


@transaction.atomic
def reject_payroll(payroll_run_id, admin_user):

    payroll_run = PayrollRun.objects.select_for_update().get(
        id=payroll_run_id
    )

    if payroll_run.status != 'SUBMITTED':
        raise ValueError('Only SUBMITTED payroll can be rejected.')

    payroll_run.status = 'REJECTED'
    payroll_run.approved_by = admin_user
    payroll_run.approved_at = timezone.now()
    payroll_run.save()

    return payroll_run

@transaction.atomic
def create_payroll_journal_entry(payroll_run_id, admin_user):

    payroll_run = PayrollRun.objects.select_for_update().get(
        id=payroll_run_id
    )

    if payroll_run.status != 'APPROVED':
        raise ValueError('Only APPROVED payroll can be posted.')

    reference = f'PAYROLL-{payroll_run.id}'

    existing_entry = JournalEntry.objects.filter(
        tenant=payroll_run.tenant,
        reference=reference
    ).first()

    if existing_entry:
        raise ValueError('Payroll has already been posted to the ledger.')

    salary_expense = Account.objects.get(
        tenant=payroll_run.tenant,
        code='5000'
    )

    paye_payable = Account.objects.get(
        tenant=payroll_run.tenant,
        code='2100'
    )

    cash_account = Account.objects.get(
        tenant=payroll_run.tenant,
        code='1000'
    )

    entry = JournalEntry.objects.create(
        tenant=payroll_run.tenant,
        store=payroll_run.store,
        reference=reference,
        description='Monthly Payroll',
        entry_date=timezone.now().date(),
        status='POSTED'
    )

    JournalLine.objects.create(
        journal_entry=entry,
        account=salary_expense,
        description='Salary Expense',
        debit=payroll_run.total_gross_salary,
        credit=Decimal('0.00')
    )

    JournalLine.objects.create(
        journal_entry=entry,
        account=paye_payable,
        description='PAYE Liability',
        debit=Decimal('0.00'),
        credit=payroll_run.total_paye
    )

    JournalLine.objects.create(
        journal_entry=entry,
        account=cash_account,
        description='Salary Payment',
        debit=Decimal('0.00'),
        credit=payroll_run.total_net_salary
    )

    ComplianceTaxLedger.objects.create(
        tenant=payroll_run.tenant,
        store=payroll_run.store,
        tax_type='PAYE',
        reference=reference,
        taxable_amount=payroll_run.total_gross_salary,
        tax_amount=payroll_run.total_paye,
        period_month=payroll_run.payroll_month,
        period_year=payroll_run.payroll_year,
        status='PAYABLE'
    )

    old_data = {
        'status': payroll_run.status
    }

    payroll_run.status = 'POSTED'
    payroll_run.posted_by = admin_user
    payroll_run.posted_at = timezone.now()
    payroll_run.save()

    AuditLog.objects.create(
        user=admin_user,
        action='PAYROLL_APPROVED_AND_POSTED',
        model_name='PayrollRun',
        object_id=payroll_run.id,
        old_data=old_data,
        new_data={
            'status': payroll_run.status,
            'tenant_id': payroll_run.tenant_id,
            'store_id': payroll_run.store_id,
            'reference': reference,
            'journal_entry_id': entry.id,
            'total_gross_salary': str(payroll_run.total_gross_salary),
            'total_paye': str(payroll_run.total_paye),
            'total_net_salary': str(payroll_run.total_net_salary),
        }
    )

    return entry