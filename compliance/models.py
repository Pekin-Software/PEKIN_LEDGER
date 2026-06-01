from django.db import models
from django.utils import timezone
from django.conf import settings

from customers.models import Client
from stores.models import Store

class EInvoice(models.Model):

    STATUS_CHOICES = (
        ("DRAFT", "Draft"),
        ("ISSUED", "Issued"),
        ("VOIDED", "Voided"),
    )

    tenant = models.ForeignKey(Client, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)

    invoice_number = models.CharField(max_length=100)

    customer_name = models.CharField(max_length=255, blank=True, null=True)
    customer_tin = models.CharField(max_length=100, blank=True, null=True)

    subtotal = models.DecimalField(max_digits=18, decimal_places=2)
    vat_total = models.DecimalField(max_digits=18, decimal_places=2)
    grand_total = models.DecimalField(max_digits=18, decimal_places=2)

    qr_code_payload = models.TextField(blank=True, null=True)
    digital_signature = models.CharField(max_length=255, blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="DRAFT")
    issued_at = models.DateTimeField(blank=True, null=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_einvoices",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("tenant", "store", "invoice_number")
        indexes = [
            models.Index(fields=["tenant", "store"]),
            models.Index(fields=["invoice_number"]),
            models.Index(fields=["status"]),
        ]

    def issue(self):
        self.status = "ISSUED"
        self.issued_at = timezone.now()
        self.save(update_fields=["status", "issued_at"])

    def __str__(self):
        return self.invoice_number


class EInvoiceLine(models.Model):

    invoice = models.ForeignKey(
        EInvoice,
        on_delete=models.CASCADE,
        related_name="lines",
    )

    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=18, decimal_places=2)
    unit_price = models.DecimalField(max_digits=18, decimal_places=2)

    taxable_amount = models.DecimalField(max_digits=18, decimal_places=2)
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2)
    vat_amount = models.DecimalField(max_digits=18, decimal_places=2)
    line_total = models.DecimalField(max_digits=18, decimal_places=2)

    tax_type = models.CharField(max_length=30)

    def __str__(self):
        return self.description


class TaxFiling(models.Model):

    STATUS_CHOICES = (
        ("DRAFT", "Draft"),
        ("READY_FOR_REVIEW", "Ready For Review"),
        ("APPROVED", "Approved"),
        ("SUBMITTED", "Submitted"),
        ("PAID", "Paid"),
        ("REJECTED", "Rejected"),
    )

    TAX_TYPES = (
        ("VAT", "VAT"),
        ("PAYE", "PAYE"),
        ("WITHHOLDING", "Withholding"),
        ("CORPORATE_INCOME_TAX", "Corporate Income Tax"),
    )

    tenant = models.ForeignKey(Client, on_delete=models.CASCADE)

    # Null store means tenant-level consolidated filing.
    store = models.ForeignKey(
        Store,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    tax_type = models.CharField(max_length=50, choices=TAX_TYPES)
    reporting_period = models.CharField(max_length=20)

    total_taxable_sales = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_exempt_sales = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    output_vat = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    input_vat = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    net_tax_payable = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    lra_reference = models.CharField(max_length=255, blank=True, null=True)
    submitted_at = models.DateTimeField(blank=True, null=True)

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_tax_filings",
    )

    approved_at = models.DateTimeField(blank=True, null=True)

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="DRAFT")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("tenant", "store", "tax_type", "reporting_period")
        indexes = [
            models.Index(fields=["tenant", "store"]),
            models.Index(fields=["tax_type", "reporting_period"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        scope = self.store.name if self.store else "CONSOLIDATED"
        return f"{scope} - {self.tax_type} - {self.reporting_period}"


class PeriodLock(models.Model):

    LOCK_TYPES = (
        ("ACCOUNTING", "Accounting"),
        ("VAT", "VAT"),
        ("POS", "POS"),
        ("INVENTORY", "Inventory"),
        ("PAYROLL", "Payroll"),
        ("FULL", "Full Period Lock"),
    )

    tenant = models.ForeignKey(Client, on_delete=models.CASCADE)

    # Null store means lock the full tenant period.
    store = models.ForeignKey(
        Store,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    reporting_period = models.CharField(max_length=20)
    lock_type = models.CharField(max_length=30, choices=LOCK_TYPES)

    is_locked = models.BooleanField(default=False)

    locked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="compliance_period_locks",
    )

    locked_at = models.DateTimeField(blank=True, null=True)
    reason = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ("tenant", "store", "reporting_period", "lock_type")
        indexes = [
            models.Index(fields=["tenant", "store"]),
            models.Index(fields=["reporting_period", "lock_type"]),
            models.Index(fields=["is_locked"]),
        ]

    def lock(self, user=None, reason=None):
        self.is_locked = True
        self.locked_by = user
        self.locked_at = timezone.now()
        self.reason = reason
        self.save(update_fields=["is_locked", "locked_by", "locked_at", "reason"])

    def __str__(self):
        scope = self.store.name if self.store else "ALL BRANCHES"
        return f"{scope} - {self.reporting_period} - {self.lock_type}"


class ComplianceAuditLog(models.Model):

    MODULE_CHOICES = (
        ("POS", "POS"),
        ("INVENTORY", "Inventory"),
        ("VAT", "VAT"),
        ("ACCOUNTING", "Accounting"),
        ("COMPLIANCE", "Compliance"),
    )

    ACTION_TYPES = (
        ("EINVOICE_CREATED", "E-Invoice Created"),
        ("EINVOICE_VERIFIED", "E-Invoice Verified"),
        ("VAT_FILING_GENERATED", "VAT Filing Generated"),
        ("TAX_FILING_APPROVED", "Tax Filing Approved"),
        ("TAX_FILING_SUBMITTED", "Tax Filing Submitted"),
        ("PERIOD_LOCKED", "Period Locked"),
        ("POS_EVENT", "POS Event"),
        ("INVENTORY_EVENT", "Inventory Event"),
        ("VAT_EVENT", "VAT Event"),
    )

    tenant = models.ForeignKey(Client, on_delete=models.CASCADE)

    store = models.ForeignKey(
        Store,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    module = models.CharField(max_length=30, choices=MODULE_CHOICES, default="COMPLIANCE")
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES)

    reference = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "store"]),
            models.Index(fields=["module", "action_type"]),
            models.Index(fields=["reference"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.action_type} - {self.reference}"


class POSComplianceEvent(models.Model):

    EVENT_TYPES = (
        ("SALE_POSTED", "Sale Posted"),
        ("SALE_REFUNDED", "Sale Refunded"),
        ("RECEIPT_PRINTED", "Receipt Printed"),
        ("VAT_POSTED", "VAT Posted"),
        ("EINVOICE_ISSUED", "E-Invoice Issued"),
    )

    tenant = models.ForeignKey(Client, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)

    sale_reference = models.CharField(max_length=255)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)

    cashier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    vat_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    is_compliant = models.BooleanField(default=True)
    note = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)


class InventoryComplianceEvent(models.Model):

    EVENT_TYPES = (
        ("STOCK_RECEIVED", "Stock Received"),
        ("STOCK_SOLD", "Stock Sold"),
        ("STOCK_TRANSFERRED", "Stock Transferred"),
        ("STOCK_ADJUSTED", "Stock Adjusted"),
        ("STOCK_WRITTEN_OFF", "Stock Written Off"),
        ("NEGATIVE_STOCK_ATTEMPT", "Negative Stock Attempt"),
        ("EXPIRED_STOCK_ATTEMPT", "Expired Stock Attempt"),
    )

    tenant = models.ForeignKey(Client, on_delete=models.CASCADE)

    store = models.ForeignKey(
        Store,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_compliance_events",
    )

    destination_store = models.ForeignKey(
        Store,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incoming_inventory_compliance_events",
    )

    reference = models.CharField(max_length=255)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)

    product_name = models.CharField(max_length=255, blank=True, null=True)
    quantity = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    is_compliant = models.BooleanField(default=True)
    note = models.TextField(blank=True, null=True)

    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

class ComplianceTaxLedger(models.Model):

    TAX_TYPES = (
        ('VAT', 'VAT'),
        ('PAYE', 'PAYE'),
        ('WITHHOLDING', 'Withholding Tax'),
        ('CORPORATE_INCOME', 'Corporate Income Tax'),
    )

    STATUS_CHOICES = (
        ('PAYABLE', 'Payable'),
        ('FILED', 'Filed'),
        ('PAID', 'Paid'),
    )

    tenant = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='compliance_tax_ledgers'
    )

    store = models.ForeignKey(
        Store,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='compliance_tax_ledgers'
    )

    tax_type = models.CharField(
        max_length=50,
        choices=TAX_TYPES
    )

    reference = models.CharField(
        max_length=100
    )

    taxable_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2
    )

    tax_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2
    )

    period_month = models.CharField(max_length=20)
    period_year = models.IntegerField()

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='PAYABLE'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (
            ('tenant', 'tax_type', 'reference'),
        )

    def __str__(self):
        return f'{self.tax_type} - {self.reference}'

class BranchVATSummary(models.Model):

    tenant = models.ForeignKey(Client, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)

    reporting_period = models.CharField(max_length=20)

    taxable_sales = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    exempt_sales = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    zero_rated_sales = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    output_vat = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    input_vat = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    net_vat = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    generated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("tenant", "store", "reporting_period")
        indexes = [
            models.Index(fields=["tenant", "store", "reporting_period"]),
        ]

    def __str__(self):
        return f"{self.store} - VAT - {self.reporting_period}"