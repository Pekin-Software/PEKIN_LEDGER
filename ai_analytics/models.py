from django.db import models
from django.utils import timezone

from customers.models import Client, User

class ComplianceRiskProfile(models.Model):

    RISK_LEVELS = (
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    )

    business_name = models.ForeignKey(Client, on_delete=models.CASCADE)

    risk_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    risk_level = models.CharField(max_length=20, choices=RISK_LEVELS, default='LOW')

    reason = models.TextField(blank=True, null=True)

    reviewed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.business_name} - {self.risk_level}'


class ComplianceAlert(models.Model):

    ALERT_TYPES = (
        ('VAT_ANOMALY', 'VAT Anomaly'),
        ('REFUND_RISK', 'Refund Risk'),
        ('PAYROLL_ANOMALY', 'Payroll Anomaly'),
        ('SALES_PATTERN', 'Sales Pattern'),
        ('FILING_OVERDUE', 'Filing Overdue'),
        ('RECONCILIATION_RISK', 'Reconciliation Risk'),
        ('FRAUD_RISK', 'Fraud Risk'),
    )

    SEVERITY_CHOICES = (
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    )

    business_name = models.ForeignKey(Client, on_delete=models.CASCADE)

    alert_type = models.CharField(max_length=50, choices=ALERT_TYPES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)

    title = models.CharField(max_length=255)
    message = models.TextField()

    reference = models.CharField(max_length=255, blank=True, null=True)

    resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    resolved_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def resolve(self, user=None):
        self.resolved = True
        self.resolved_by = user
        self.resolved_at = timezone.now()
        self.save(update_fields=['resolved', 'resolved_by', 'resolved_at'])

    def __str__(self):
        return self.title


class ComplianceAnalysisRun(models.Model):

    ANALYSIS_TYPES = (
        ('FULL', 'Full Compliance Analysis'),
        ('VAT', 'VAT Analysis'),
        ('PAYROLL', 'Payroll Analysis'),
        ('SALES', 'Sales Analysis'),
        ('FRAUD', 'Fraud Analysis'),
    )

    business_name = models.ForeignKey(Client, on_delete=models.CASCADE)

    analysis_type = models.CharField(max_length=30, choices=ANALYSIS_TYPES)
    reporting_period = models.CharField(max_length=20, blank=True, null=True)

    total_alerts = models.IntegerField(default=0)
    highest_risk_level = models.CharField(max_length=20, default='LOW')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.analysis_type} - {self.reporting_period}'