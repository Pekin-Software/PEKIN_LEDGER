from django.db import models
from django.conf import settings

from customers.models import Client
from payroll.models import PayrollRun
from compliance.models import ComplianceTaxLedger
from stores.models import Store
from inventory.models import Supplier, Purchase
from sales.models import Sale

# models.py
class CashTransaction(models.Model):

    TRANSACTION_TYPES = (
        ('SALE', 'Sale'),
        ('PAYROLL_PAYMENT', 'Payroll Payment'),
        ('PAYE_PAYMENT', 'PAYE Payment'),
    )

    tenant = models.ForeignKey(Client, on_delete=models.CASCADE)

    store = models.ForeignKey(Store, on_delete=models.CASCADE)

    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name="cash_transactions",
        null=True,
        blank=True
    )

    transaction_type = models.CharField(
        max_length=50,
        choices=TRANSACTION_TYPES,
        default='SALE'
    )

    cashier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    amount = models.DecimalField(max_digits=18, decimal_places=2)

    transaction_reference = models.CharField(
        max_length=255,
        unique=True
    )

    transaction_date = models.DateTimeField(auto_now_add=True)

    is_reconciled = models.BooleanField(default=False)

    cash_reconciliation = models.ForeignKey(
        "CashReconciliation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cash_transactions"
    )

    created_at = models.DateTimeField(auto_now_add=True)

class CashReconciliation(models.Model):

    STATUS_CHOICES = (
        ('MATCHED', 'Matched'),
        ('SHORTAGE', 'Shortage'),
        ('OVERAGE', 'Overage'),
    )

    tenant = models.ForeignKey(
        Client,
        on_delete=models.CASCADE
    )

    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE
    )

    cashier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    opening_cash = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0
    )

    system_cash_sales = models.DecimalField(
        max_digits=18,
        decimal_places=2
    )

    counted_cash = models.DecimalField(
        max_digits=18,
        decimal_places=2
    )

    variance = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES
    )

    shift_reference = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    reconciled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cash_reconciliations_done'
    )

    reconciled_at = models.DateTimeField(
        auto_now_add=True
    )

class MobileMoneyTransaction(models.Model):

    PROVIDERS = (
        ('ORANGE', 'Orange Money'),
        ('MTN', 'MTN Mobile Money'),
    )

    TRANSACTION_TYPES = (
        ('SALE', 'Sale'),
        ('PAYROLL_PAYMENT', 'Payroll Payment'),
        ('PAYE_PAYMENT', 'PAYE Payment'),
    )

    tenant = models.ForeignKey(Client, on_delete=models.CASCADE)

    store = models.ForeignKey(Store, on_delete=models.CASCADE)

    provider = models.CharField(
        max_length=30,
        choices=PROVIDERS
    )

    transaction_type = models.CharField(
        max_length=50,
        choices=TRANSACTION_TYPES,
        default='SALE'
    )

    transaction_reference = models.CharField(
        max_length=255,
        unique=True
    )

    customer_number = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    amount = models.DecimalField(max_digits=18, decimal_places=2)

    transaction_date = models.DateTimeField()

    is_reconciled = models.BooleanField(default=False)

    reconciled_at = models.DateTimeField(null=True, blank=True)

    reconciled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    sale = models.ForeignKey(
        Sale,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='momo_transactions'
    )

    matched_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0
    )

    remaining_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0
    )

    is_partial_match = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.transaction_reference

class MobileMoneyReconciliation(models.Model):

    STATUS_CHOICES = (
        ('MATCHED', 'Matched'),
        ('MISMATCH', 'Mismatch'),
        ('PENDING', 'Pending'),
    )

    tenant = models.ForeignKey(
        Client,
        on_delete=models.CASCADE
    )

    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE
    )

    momo_transaction = models.ForeignKey(
        MobileMoneyTransaction,
        on_delete=models.CASCADE,
        related_name='reconciliations'
    )

    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name='momo_reconciliations'
    )

    expected_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2
    )

    actual_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2
    )

    variance_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='PENDING'
    )

    reconciled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    reconciled_at = models.DateTimeField(
        auto_now_add=True
    )

class PayrollPaymentReconciliation(models.Model):

    PAYMENT_METHODS = (
        ('CASH', 'Cash'),
        ('MOBILE_MONEY', 'Mobile Money'),
    )

    STATUS_CHOICES = (
        ('MATCHED', 'Matched'),
        ('MISMATCH', 'Mismatch'),
        ('PARTIAL', 'Partial'),
    )

    tenant = models.ForeignKey(Client, on_delete=models.CASCADE)

    store = models.ForeignKey(Store, on_delete=models.CASCADE)

    payroll_run = models.ForeignKey(
        PayrollRun,
        on_delete=models.CASCADE,
        related_name='payment_reconciliations'
    )

    payment_method = models.CharField(
        max_length=30,
        choices=PAYMENT_METHODS
    )

    cash_transaction = models.ForeignKey(
        CashTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    mobile_money_transaction = models.ForeignKey(
        MobileMoneyTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    expected_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2
    )

    actual_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2
    )

    variance_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES
    )

    reconciled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    reconciled_at = models.DateTimeField(auto_now_add=True)

class PAYEPaymentReconciliation(models.Model):

    PAYMENT_METHODS = (
        ('CASH', 'Cash'),
        ('MOBILE_MONEY', 'Mobile Money'),
    )

    STATUS_CHOICES = (
        ('MATCHED', 'Matched'),
        ('MISMATCH', 'Mismatch'),
        ('PARTIAL', 'Partial'),
    )

    tenant = models.ForeignKey(Client, on_delete=models.CASCADE)

    store = models.ForeignKey(Store, on_delete=models.CASCADE)

    compliance_tax = models.ForeignKey(
        ComplianceTaxLedger,
        on_delete=models.CASCADE,
        related_name='paye_payment_reconciliations'
    )

    payment_method = models.CharField(
        max_length=30,
        choices=PAYMENT_METHODS
    )

    cash_transaction = models.ForeignKey(
        CashTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    mobile_money_transaction = models.ForeignKey(
        MobileMoneyTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    expected_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2
    )

    actual_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2
    )

    variance_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES
    )

    reconciled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    reconciled_at = models.DateTimeField(auto_now_add=True)

class SupplierVATTransaction(models.Model):

    tenant = models.ForeignKey(
        Client,
        on_delete=models.CASCADE
    )

    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE
    )

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE
    )

    purchase = models.ForeignKey(
        Purchase,
        on_delete=models.CASCADE,
        related_name='supplier_vat_transactions'
    )

    supplier_invoice_number = models.CharField(
        max_length=255
    )

    supplier_vat_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2
    )

    transaction_date = models.DateField(
        auto_now_add=True
    )

    is_reconciled = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

class SupplierVATReconciliation(models.Model):

    STATUS_CHOICES = (
        ('MATCHED', 'Matched'),
        ('MISMATCH', 'Mismatch'),
        ('PENDING', 'Pending'),
    )

    tenant = models.ForeignKey(
        Client,
        on_delete=models.CASCADE
    )

    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE
    )

    supplier_vat_transaction = models.ForeignKey(
        SupplierVATTransaction,
        on_delete=models.CASCADE,
        related_name='reconciliations',
        null=True,
        blank=True
    )

    purchase = models.ForeignKey(
        Purchase,
        on_delete=models.CASCADE
    )

    expected_vat_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2
    )

    actual_vat_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2
    )

    variance_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='PENDING'
    )

    reconciled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    reconciled_at = models.DateTimeField(
        auto_now_add=True
    )

class ReconciliationException(models.Model):

    EXCEPTION_TYPES = (
        ('CASH_SHORTAGE', 'Cash Shortage'),
        ('CASH_OVERAGE', 'Cash Overage'),
        ('MOMO_MISMATCH', 'Mobile Money Mismatch'),
        ('VAT_VARIANCE', 'VAT Variance'),
    )

    tenant = models.ForeignKey(
        Client,
        on_delete=models.CASCADE
    )

    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    exception_type = models.CharField(
        max_length=50,
        choices=EXCEPTION_TYPES
    )

    reference = models.CharField(
        max_length=255
    )

    expected_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2
    )

    actual_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2
    )

    variance = models.DecimalField(
        max_digits=18,
        decimal_places=2
    )

    resolved = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

