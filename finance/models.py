from django.db import models, transaction
from django.utils import timezone
from customers.models import Client

class ExchangeRate(models.Model):
    tenant = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="exchange_rates")
    usd_rate = models.DecimalField(max_digits=10, decimal_places=2)
    effective_date = models.DateField(editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('tenant', 'effective_date')
        ordering = ['-effective_date']

    def save(self, *args, **kwargs):
        if not self.pk:  # Only set on creation
            self.effective_date = timezone.now().date()
        super().save(*args, **kwargs)

    def __str__(self):
        return f" {self.tenant.name} USD Rate: {self.usd_rate} (Effective: {self.effective_date})"

