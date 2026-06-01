from django.db import models
from customers.models import User 
from customers.models import Client


class Store(models.Model):
    tenant = models.ForeignKey(Client, on_delete=models.CASCADE)
    store_name = models.CharField(max_length=100)
    branch_code = models.CharField( max_length=20, null=True, blank=True, help_text="Unique accounting branch/store code")
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100, default='N/A')
    country = models.CharField(max_length=100, default='N/A')
    phone_number = models.CharField(max_length=20, default='N/A')

    is_main_store = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.branch_code} - {self.store_name}"

    class Meta:
        unique_together = ('tenant', 'branch_code')


class StoreUserAssignment(models.Model):
    tenant = models.ForeignKey(
        Client,
        on_delete=models.CASCADE
    )

    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="user_assignments"
    )

    user_id = models.PositiveIntegerField()

    position = models.CharField(
        max_length=50,
        choices=[
            ("Admin", "Admin"),
            ("Manager", "Manager"),
            ("Cashier", "Cashier"),
            ("ACCOUNTANT", "Accountant"),
            ("AUDITOR", "Auditor"),
        ]
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("tenant", "store", "user_id")

    def __str__(self):
        return f"{self.user_id} - {self.store.store_name}"
