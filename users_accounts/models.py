from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, Group, Permission
from django.db import models
from django_tenants.models import TenantMixin, DomainMixin
import re
from django.db import connection, transaction
from django.db.utils import IntegrityError

class UserManager(BaseUserManager):
    def create_user(self, email, first_name, last_name, business_name, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, first_name=first_name, last_name=last_name, business_name=business_name, **extra_fields)
        if password:
            user.set_password(password)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    first_name = models.CharField(max_length=50)
    middle_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    phone1 = models.CharField(max_length=20, unique=True)
    phone2 = models.CharField(max_length=20, blank=True, null=True)
    photo = models.ImageField(upload_to="profile_photos/", blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    nationality = models.CharField(max_length=50, blank=True, null=True)
    business_name = models.CharField(max_length=100, blank=True, null=True)  # Business name

    POSITION_CHOICES = [("Owner", "Owner"), ("Manager", "Manager"), ("Employee", "Employee")]
    position = models.CharField(max_length=20, choices=POSITION_CHOICES, default="Owner")

    parent_owner = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="sub_accounts")

    groups = models.ManyToManyField(Group, related_name="custom_user_groups", blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name="custom_user_permissions", blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name", "business_name"]

    @property
    def full_name(self):
        return f"{self.first_name} {self.middle_name or ''} {self.last_name}".strip()

    def save(self, *args, **kwargs):
        if not self.pk and not User.objects.exists():  # First user should be Owner by default
            self.position = "Owner"
        elif self.position in ["Manager", "Employee"] and not self.parent_owner:
            raise ValueError("Manager and Employee must be linked to an Owner account.")

        super().save(*args, **kwargs)