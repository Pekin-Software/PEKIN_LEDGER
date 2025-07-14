from django.core.exceptions import ValidationError
import re
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django_tenants.models import TenantMixin, DomainMixin
from django.utils.translation import gettext_lazy as _
from django_tenants.utils import schema_context
from django.apps import apps

#Functions for Validation
def validate_name(value):
    if not re.match(r'^[a-zA-Z-]+$', value):
        raise ValidationError(_('Names can only contain letters and hyphens (-)'))
    return value

def validate_phone(value):
    if not re.match(r'^\+?\d+$', value):
        raise ValidationError(_('Phone numbers must contain only digits and an optional leading "+"'))
    return value

class Client(TenantMixin):
    business_name = models.CharField(max_length=100)
    schema_name = models.CharField(max_length=50, unique=True) 
    created_on = models.DateField(auto_now_add=True)
    
    def get_domain(self):
        domain = Domain.objects.filter(tenant=self).first()
        return domain.domain if domain else None
class Domain(DomainMixin):
   pass

# Custom Manager for User Model
class CustomUserManager(BaseUserManager):
    def create_user(self, email, username, password=None, business_name=None, **extra_fields):
        """Create and return a user with an email and password"""
        if not email:
            raise ValueError(_('The Email field must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)

        if password:
            user.set_password(password)  # This will hash the password properly

        # Generate a valid schema_name
        if business_name:
            schema_name = re.sub(r'[^a-z0-9_]', '', business_name.lower().replace(" ", ""))
            if not schema_name or schema_name[0].isdigit():
                raise ValueError(_('Invalid schema name generated from business_name'))

            # Ensure schema_name is unique
            base_schema_name = schema_name
            counter = 1
            while Client.objects.filter(schema_name=schema_name).exists():
                schema_name = f"{base_schema_name}{counter}"
                counter += 1  # Increment until a unique schema name is found
            
            # Create Client (Tenant)
            client = Client.objects.create(business_name=business_name, schema_name=schema_name)

            # Fetch the base domain from the public schema
            public_domain = Domain.objects.filter(tenant__schema_name="public").first()
            if public_domain:
                base_domain = ".".join(public_domain.domain.split(".")[-2:])  # Extr"
            else:
                raise ValueError(_("Public schema domain not found. Please ensure it exists."))

            # Generate a unique domain name using the public domain
            domain_name = f"{schema_name}.{base_domain}"
            counter = 1
            while Domain.objects.filter(domain=domain_name).exists():
                domain_name = f"{schema_name}{counter}.{base_domain}"
                counter += 1  # Ensure uniqueness
            
            # Create Domain instance
            Domain.objects.create(domain=domain_name, tenant=client, is_primary=True)

            # Assign user to the created tenant
            user.domain = client

            with schema_context(client.schema_name):
                user.save(using=self._db)

                # ✅ Create the default warehouse here
                Warehouse = apps.get_model('inventory', 'Warehouse')
                Warehouse.objects.create(
                    tenant=client,
                    name=f"{business_name}'s General Warehouse",
                    location="Main Distribution Center",
                    warehouse_type="general"
                )

            # Activate schema and create tables
            with schema_context(client.schema_name):
                user.save(using=self._db)
                
        return user

class User(AbstractBaseUser):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=30, unique=True)
    first_name = models.CharField(max_length=50, blank=True, null=False, validators=[validate_name])
    middle_name = models.CharField(max_length=50, blank=True, null=True, validators=[validate_name])
    last_name = models.CharField(max_length=50, blank=True, null=False, validators=[validate_name])
    phone1 = models.CharField(max_length=15, blank=False, null=False, validators=[validate_phone])
    phone2 = models.CharField(max_length=15, blank=True, null=True, validators=[validate_phone])
    photo = models.ImageField(upload_to='profile_photos/', blank=True, null=True)
    address = models.CharField(max_length=255, blank=False, null=False)
    city = models.CharField(max_length=100, blank=False, null=False)
    country = models.CharField(max_length=100, blank=False, null=False)
    date_of_birth = models.DateField(blank=False, null=False)
    nationality = models.CharField(max_length=100, blank=False, null=False)
    position = models.CharField(max_length=50, choices=[('Admin', 'Admin'), ('Manager', 'Manager'), ('Cashier', 'Cashier')], default='Admin')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    domain = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="users", null=False)
    created_on = models.DateTimeField(auto_now_add=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'first_name', 'last_name', 'phone1', 'address', 'city', 'country', 'date_of_birth', 'nationality', 'position']

    def __str__(self):
        return self.username

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True

    @property
    def get_full_name(self):
        """Concatenate first, middle, and last name."""
        return f"{self.first_name} {self.middle_name or ''} {self.last_name}".strip()

    def can_create_subaccount(self):
        """Check if user can create subaccounts (only Admins can create them)."""
        return self.position == 'Admin'
