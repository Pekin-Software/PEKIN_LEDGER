from django.db import models
from django.db import connection 
from customers.models import User  # Assuming User model is in the 'customer' app
from customers.models import Client
class Store(models.Model):
    tenant = models.ForeignKey(Client, on_delete=models.CASCADE) 
    store_name = models.CharField(max_length=100)
    location = models.CharField(max_length=255)
    
    def __str__(self):
        return self.store_name

class Employee(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='employees')
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='employees')
    date_assigned = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.store.store_name} ({self.user.position})"  # Accessing position from User model

    class Meta:
        unique_together = ('store', 'user')

