from django.db import models
from django.conf import settings
from customers.models import Client
from stores.models import Store

class Account(models.Model):

    ACCOUNT_TYPES = (
        ('ASSET', 'Asset'),
        ('LIABILITY', 'Liability'),
        ('EQUITY', 'Equity'),
        ('REVENUE', 'Revenue'),
        ('EXPENSE', 'Expense'),
    )

    tenant = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="accounts",
        null=True,
        blank=True
    )

    code = models.CharField(
        max_length=20
    )

    name = models.CharField(
        max_length=255
    )

    account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_TYPES
    )

    is_active = models.BooleanField(
        default=True
    )

    class Meta:

        unique_together = (
            'tenant',
            'code'
        )

    def __str__(self):

        return (
            f'{self.code} - {self.name}'
        )

class JournalEntry(models.Model):

    STATUS_CHOICES = (
        ('DRAFT', 'Draft'),
        ('POSTED', 'Posted'),
        ('REVERSED', 'Reversed'),
    )

    tenant = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="journal_entries",
        null=True,
        blank=True
    )

    store = models.ForeignKey(
    Store,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="journal_entries"
    )
    CASH_FLOW_CATEGORIES = (
    ('OPERATING', 'Operating'),
    ('INVESTING', 'Investing'),
    ('FINANCING', 'Financing'),
)

    cash_flow_category = models.CharField(
        max_length=20,
        choices=CASH_FLOW_CATEGORIES,
        null=True,
        blank=True
    )
    is_reconciled = models.BooleanField(default=False)

    reconciliation_reference = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    is_inter_store = models.BooleanField(default=False)

    source_store = models.ForeignKey(
        Store,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="source_inter_store_entries"
    )

    destination_store = models.ForeignKey(
        Store,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="destination_inter_store_entries"
    )

    reference = models.CharField(max_length=100, unique=True)
    description = models.TextField()

    entry_date = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT'
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.reference


class JournalLine(models.Model):

    journal_entry = models.ForeignKey(
        JournalEntry,
        on_delete=models.CASCADE,
        related_name='lines'
    )
    
    store = models.ForeignKey(
        Store,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="journal_lines"
    )

    is_reconciled = models.BooleanField(default=False)

    reconciliation_reference = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE
    )

    description = models.CharField(max_length=255)

    debit = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0
    )

    credit = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0
    )

    def __str__(self):
        return self.description
