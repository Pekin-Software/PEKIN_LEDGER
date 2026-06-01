from rest_framework.exceptions import PermissionDenied
from stores.models import StoreUserAssignment


class ComplianceAccessMixin:

    STORE_ALLOWED_ROLES = [
        "Manager",
        "Admin",
        "ACCOUNTANT",
        "AUDITOR",
    ]

    MASTER_ALLOWED_ROLES = [
        "Admin",
        "ACCOUNTANT",
        "AUDITOR",
    ]

    def get_tenant(self, request):
        return request.tenant

    def get_user_store(self, request):
        return getattr(request.user, "store", None)

    def verify_store_permission(
        self,
        request,
        store,
        resource_name="resource"
    ):
        user = request.user
        tenant = self.get_tenant(request)

        if user.position == "Cashier":
            raise PermissionDenied(
                f"You are not allowed to access {resource_name}."
            )

        if user.position not in self.STORE_ALLOWED_ROLES:
            raise PermissionDenied(
                f"You are not allowed to access {resource_name}."
            )

        if store.tenant_id != tenant.id:
            raise PermissionDenied(
                f"This store does not belong to your tenant."
            )

        if user.position == "Manager":
            assignment = StoreUserAssignment.objects.filter(
                tenant=tenant,
                store=store,
                user_id=user.id,
                is_active=True
            ).first()

            if not assignment:
                raise PermissionDenied(
                    f"You cannot access another store's {resource_name}."
                )

        return True

    def verify_master_permission(
        self,
        request,
        resource_name="master resource"
    ):
        user = request.user

        if user.position not in self.MASTER_ALLOWED_ROLES:
            raise PermissionDenied(
                f"You are not allowed to access {resource_name}."
            )

        return True

class ReconciliationAccessMixin:

    STORE_ALLOWED_ROLES = [
        "Manager",
        "Admin",
        "ACCOUNTANT",
        "AUDITOR",
    ]

    MASTER_ALLOWED_ROLES = [
        "Admin",
        "ACCOUNTANT",
        "AUDITOR",
    ]

    def get_tenant(self, request):
        return request.user.tenant

    def get_user_store(self, request):
        return getattr(request.user, "store", None)

    def verify_store_permission(
        self,
        request,
        store,
        resource_name="resource"
    ):
        user = request.user
        tenant = self.get_tenant(request)

        if user.position == "Cashier":
            raise PermissionDenied(
                f"You are not allowed to access {resource_name}."
            )

        if user.position not in self.STORE_ALLOWED_ROLES:
            raise PermissionDenied(
                f"You are not allowed to access {resource_name}."
            )

        if user.position == "Manager":
            assignment = StoreUserAssignment.objects.filter(
                tenant=tenant,
                store=store,
                user_id=user.id,
                is_active=True
            ).first()

            if not assignment:
                raise PermissionDenied(
                    f"You cannot access another store's {resource_name}."
                )

        return True

    def verify_master_permission(
        self,
        request,
        resource_name="master resource"
    ):
        user = request.user

        if user.position not in self.MASTER_ALLOWED_ROLES:
            raise PermissionDenied(
                f"You are not allowed to access {resource_name}."
            )

        return True