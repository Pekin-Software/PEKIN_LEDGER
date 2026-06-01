from django.db import models

from customers.models import Client, User
from stores.models import Store


class Employee(models.Model):

    EMPLOYMENT_STATUS = (
        ('ACTIVE', 'Active'),
        ('TERMINATED', 'Terminated'),
        ('SUSPENDED', 'Suspended'),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='employee_profile'
    )

    employee_id = models.CharField(
        max_length=100,
        unique=True
    )

    base_salary = models.DecimalField(
        max_digits=18,
        decimal_places=2
    )

    employment_status = models.CharField(
        max_length=30,
        choices=EMPLOYMENT_STATUS,
        default='ACTIVE'
    )

    hired_date = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.employee_id}"


class PAYETaxBracket(models.Model):

    tenant = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='paye_tax_brackets'
    )

    min_income = models.DecimalField(max_digits=18, decimal_places=2)
    max_income = models.DecimalField(max_digits=18, decimal_places=2)
    rate = models.DecimalField(max_digits=5, decimal_places=2)

    effective_date = models.DateField()

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.min_income} - {self.max_income} @ {self.rate}%'


class PayrollRun(models.Model):

    STATUS_CHOICES = (
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('POSTED', 'Posted'),
    )

    tenant = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='payroll_runs'
    )

    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='payroll_runs'
    )

    payroll_month = models.CharField(max_length=20)
    payroll_year = models.IntegerField()

    total_gross_salary = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0
    )

    total_paye = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0
    )

    total_net_salary = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT'
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_payroll_runs'
    )

    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_payroll_runs'
    )

    approved_at = models.DateTimeField(null=True, blank=True)

    posted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='posted_payroll_runs'
    )

    posted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (
            ('tenant', 'store', 'payroll_month', 'payroll_year'),
        )

    def __str__(self):
        return f'{self.store.store_name} - {self.payroll_month}-{self.payroll_year}'


class PayrollItem(models.Model):

    payroll_run = models.ForeignKey(
        PayrollRun,
        on_delete=models.CASCADE,
        related_name='items'
    )

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='payroll_items'
    )

    gross_salary = models.DecimalField(max_digits=18, decimal_places=2)

    paye_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0
    )

    withholding_tax = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0
    )

    deductions = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0
    )

    net_salary = models.DecimalField(max_digits=18, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (
            ('payroll_run', 'employee'),
        )