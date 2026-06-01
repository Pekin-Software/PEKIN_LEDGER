from decimal import Decimal

from django.db import models
from django.utils import timezone
from django.conf import settings
from customers.models import Client, User

from stores.models import Store


class TaxClass(models.Model):

    TAX_TYPES = (
        ("VATABLE", "Vatable"),
        ("EXEMPT", "Exempt"),
        ("ZERO_RATED", "Zero Rated"),
    )

    tenant = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="tax_classes"
    )

    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)

    tax_type = models.CharField(max_length=30, choices=TAX_TYPES)

    rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00")
    )

    effective_date = models.DateField()
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("tenant", "code")
        ordering = ["code"]

    def __str__(self):
        return f"{self.tenant} - {self.name}"


class TaxPeriod(models.Model):

    STATUS_CHOICES = (
        ("OPEN", "Open"),
        ("STORE_REVIEW", "Store Review"),
        ("ADMIN_REVIEW", "Admin Review"),
        ("APPROVED", "Approved"),
        ("FILED", "Filed"),
        ("LOCKED", "Locked"),
    )

    tenant = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="tax_periods"
    )

    period = models.CharField(max_length=20)  # Example: 2026-04

    start_date = models.DateField()
    end_date = models.DateField()

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="OPEN"
    )

    is_locked = models.BooleanField(default=False)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_tax_periods"
    )

    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_tax_periods"
    )

    approved_at = models.DateTimeField(null=True, blank=True)

    locked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="locked_tax_periods"
    )

    locked_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("tenant", "period")
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.tenant} - {self.period}"

class VATLedger(models.Model):

    VAT_TYPES = (
        ("INPUT", "Input VAT"),
        ("OUTPUT", "Output VAT"),
        ("ADJUSTMENT", "Adjustment"),
    )

    SOURCE_TYPES = (
        ("SALE", "Sale"),
        ("PURCHASE", "Purchase"),
        ("EXPENSE", "Expense"),
        ("RETURN", "Return"),
        ("MANUAL_ADJUSTMENT", "Manual Adjustment"),
    )

    tenant = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="vat_ledgers"
    )

    store = models.ForeignKey(
        "stores.Store",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vat_ledgers"
    )

    vat_type = models.CharField(max_length=20, choices=VAT_TYPES)

    source_type = models.CharField(
        max_length=30,
        choices=SOURCE_TYPES
    )

    transaction_reference = models.CharField(max_length=255)

    taxable_amount = models.DecimalField(max_digits=18, decimal_places=2)
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2)
    vat_amount = models.DecimalField(max_digits=18, decimal_places=2)

    reporting_period = models.CharField(max_length=20)  # Example: 2026-06

    tax_type = models.CharField(
        max_length=30,
        choices=(
            ("VATABLE", "Vatable"),
            ("EXEMPT", "Exempt"),
            ("ZERO_RATED", "Zero Rated"),
        ),
        default="VATABLE"
    )

    description = models.TextField(blank=True, null=True)

    is_reversed = models.BooleanField(default=False)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "store"]),
            models.Index(fields=["tenant", "reporting_period"]),
            models.Index(fields=["transaction_reference"]),
            models.Index(fields=["vat_type"]),
        ]

    def __str__(self):
        return f"{self.vat_type} - {self.transaction_reference}"

class StoreVATSummary(models.Model):

    STATUS_CHOICES = (
        ("DRAFT", "Draft"),
        ("SUBMITTED", "Submitted"),
        ("REJECTED", "Rejected"),
        ("APPROVED", "Approved"),
    )

    tenant = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="store_vat_summaries"
    )

    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="vat_summaries"
    )

    tax_period = models.ForeignKey(
        TaxPeriod,
        on_delete=models.CASCADE,
        related_name="store_summaries"
    )

    output_vat = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    input_vat = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    adjustment_vat = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    net_vat_payable = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="DRAFT"
    )

    submitted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_store_vat_summaries"
    )

    submitted_at = models.DateTimeField(null=True, blank=True)

    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_store_vat_summaries"
    )

    reviewed_at = models.DateTimeField(null=True, blank=True)

    rejection_reason = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("tenant", "store", "tax_period")

    def __str__(self):
        return f"{self.store} - {self.tax_period.period}"


class VATReturn(models.Model):

    STATUS_CHOICES = (
        ("DRAFT", "Draft"),
        ("UNDER_REVIEW", "Under Review"),
        ("APPROVED", "Approved"),
        ("FILED", "Filed"),
        ("PAID", "Paid"),
    )

    tenant = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="vat_returns"
    )

    tax_period = models.OneToOneField(
        TaxPeriod,
        on_delete=models.PROTECT,
        related_name="vat_return"
    )

    total_output_vat = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_input_vat = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_adjustment_vat = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    net_vat_payable = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    carried_forward_credit = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="DRAFT"
    )

    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_vat_returns"
    )

    approved_at = models.DateTimeField(null=True, blank=True)

    filed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="filed_vat_returns"
    )

    filed_at = models.DateTimeField(null=True, blank=True)

    filing_reference = models.CharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"VAT Return - {self.tenant} - {self.tax_period.period}"


class VATAdjustment(models.Model):

    ADJUSTMENT_TYPES = (
        ("INCREASE_OUTPUT", "Increase Output VAT"),
        ("DECREASE_OUTPUT", "Decrease Output VAT"),
        ("INCREASE_INPUT", "Increase Input VAT"),
        ("DECREASE_INPUT", "Decrease Input VAT"),
    )

    tenant = models.ForeignKey(Client, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.SET_NULL, null=True, blank=True)
    tax_period = models.ForeignKey(TaxPeriod, on_delete=models.PROTECT)

    adjustment_type = models.CharField(max_length=30, choices=ADJUSTMENT_TYPES)

    amount = models.DecimalField(max_digits=18, decimal_places=2)
    reason = models.TextField()

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_vat_adjustments"
    )

    is_approved = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.adjustment_type} - {self.amount}"


class TaxPayment(models.Model):

    PAYMENT_METHODS = (
        ("BANK_TRANSFER", "Bank Transfer"),
        ("MOBILE_MONEY", "Mobile Money"),
        ("CASH", "Cash"),
        ("OTHER", "Other"),
    )

    tenant = models.ForeignKey(Client, on_delete=models.CASCADE)
    vat_return = models.ForeignKey(
        VATReturn,
        on_delete=models.PROTECT,
        related_name="payments"
    )

    amount = models.DecimalField(max_digits=18, decimal_places=2)

    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHODS)
    transaction_reference = models.CharField(max_length=255)

    paid_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    paid_at = models.DateTimeField(default=timezone.now)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"VAT Payment - {self.amount}"