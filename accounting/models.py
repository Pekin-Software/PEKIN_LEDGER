from django.db import models
from django.conf import settings

class FiscalYear(models.Model):

    year = models.IntegerField(
        unique=True
    )

    start_date = models.DateField()

    end_date = models.DateField()

    is_closed = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):

        return str(self.year)


class AccountingPeriod(models.Model):

    fiscal_year = models.ForeignKey(
        FiscalYear,
        on_delete=models.CASCADE,
        related_name='periods'
    )

    name = models.CharField(
        max_length=100
    )

    start_date = models.DateField()

    end_date = models.DateField()

    is_closed = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):

        return self.name


class PeriodLock(models.Model):

    period = models.OneToOneField(
        AccountingPeriod,
        on_delete=models.CASCADE,
        related_name='lock'
    )

    locked_by = models.ForeignKey(
            settings.AUTH_USER_MODEL,
            on_delete=models.SET_NULL,
            null=True,
            blank=True,
            related_name="accounting_period_locks"
        )

    locked_at = models.DateTimeField(
        auto_now_add=True
    )

    reason = models.TextField(
        blank=True,
        null=True
    )

    def __str__(self):

        return (
            f"Lock - {self.period.name}"
        )