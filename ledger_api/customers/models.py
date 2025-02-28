from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models
from django_tenants.models import TenantMixin, DomainMixin
from django.utils.translation import gettext_lazy as _
import re
from django_tenants.utils import schema_context

# Create a Client model for tenants (which will inherit from TenantMixin)
class Client(TenantMixin):
    business_name = models.CharField(max_length=100)
    schema_name = models.CharField(max_length=50, unique=True) 
    created_on = models.DateField(auto_now_add=True)
    
class Domain(DomainMixin):
   pass

# Custom Manager for User Model
# class CustomUserManager(BaseUserManager):
#     def create_user(self, email, username, password=None, business_name=None, **extra_fields):
#         """Create and return a user with an email and password"""
#         if not email:
#             raise ValueError(_('The Email field must be set'))
#         email = self.normalize_email(email)
#         user = self.model(email=email, username=username, **extra_fields)
#         user.set_password(password)

#         if business_name:
#             # 1️⃣ Generate a valid schema_name
#             schema_name = re.sub(r'[^a-z0-9_]', '', business_name.lower().replace(" ", ""))
#             if not schema_name or schema_name[0].isdigit():
#                 raise ValueError(_('Invalid schema name generated from business_name'))

#             # 2️⃣ Ensure schema_name is unique
#             base_schema_name = schema_name
#             counter = 1
#             while Client.objects.filter(schema_name=schema_name).exists():
#                 schema_name = f"{base_schema_name}{counter}"
#                 counter += 1  # Increment until a unique schema name is found
            
#             # 3️⃣ Create Client (Tenant)
#             client = Client.objects.create(business_name=business_name, schema_name=schema_name)

#             # 4️⃣ Fetch the base domain from the public schema
#             public_domain = Domain.objects.filter(tenant__schema_name="public").first()
#             if public_domain:
#                 base_domain = ".".join(public_domain.domain.split(".")[-2:])  # Extract "yourdomain.com"
#             else:
#                 raise ValueError(_("Public schema domain not found. Please ensure it exists."))

#             # 5️⃣ Generate a unique domain name using the public domain
#             domain_name = f"{schema_name}.{base_domain}"
#             counter = 1
#             while Domain.objects.filter(domain=domain_name).exists():
#                 domain_name = f"{schema_name}{counter}.{base_domain}"
#                 counter += 1  # Ensure uniqueness
            
#             # 6️⃣ Create Domain instance
#             Domain.objects.create(domain=domain_name, tenant=client, is_primary=True)

#             # 7️⃣ Assign user to the created tenant
#             user.domain = client

#             # 8️⃣ Activate schema and create tables
#             with schema_context(client.schema_name):
#                 user.save(using=self._db)

#         return user


class CustomUserManager(BaseUserManager):
    def create_user(self, email, username, password=None, business_name=None, **extra_fields):
        """Create and return a user with an email and password"""
        if not email:
            raise ValueError(_('The Email field must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)

        # Ensure password is hashed
        if password:
            user.set_password(password)  # This will hash the password properly

        if business_name:
            # 1️⃣ Generate a valid schema_name
            schema_name = re.sub(r'[^a-z0-9_]', '', business_name.lower().replace(" ", ""))
            if not schema_name or schema_name[0].isdigit():
                raise ValueError(_('Invalid schema name generated from business_name'))

            # 2️⃣ Ensure schema_name is unique
            base_schema_name = schema_name
            counter = 1
            while Client.objects.filter(schema_name=schema_name).exists():
                schema_name = f"{base_schema_name}{counter}"
                counter += 1  # Increment until a unique schema name is found
            
            # 3️⃣ Create Client (Tenant)
            client = Client.objects.create(business_name=business_name, schema_name=schema_name)

            # 4️⃣ Fetch the base domain from the public schema
            public_domain = Domain.objects.filter(tenant__schema_name="public").first()
            if public_domain:
                base_domain = ".".join(public_domain.domain.split(".")[-2:])  # Extract "yourdomain.com"
            else:
                raise ValueError(_("Public schema domain not found. Please ensure it exists."))

            # 5️⃣ Generate a unique domain name using the public domain
            domain_name = f"{schema_name}.{base_domain}"
            counter = 1
            while Domain.objects.filter(domain=domain_name).exists():
                domain_name = f"{schema_name}{counter}.{base_domain}"
                counter += 1  # Ensure uniqueness
            
            # 6️⃣ Create Domain instance
            Domain.objects.create(domain=domain_name, tenant=client, is_primary=True)

            # 7️⃣ Assign user to the created tenant
            user.domain = client

            # 8️⃣ Activate schema and create tables
            with schema_context(client.schema_name):
                user.save(using=self._db)

        return user


class User(AbstractBaseUser):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=30, unique=True)
    full_name = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  # Superuser flag
    is_superuser = models.BooleanField(default=False)  # Admin flag

    # Add custom fields
    domain = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="users")

    created_on = models.DateTimeField(auto_now_add=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    def __str__(self):
        return self.username

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True


