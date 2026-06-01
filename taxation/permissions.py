from rest_framework.permissions import BasePermission


def is_admin(user):
    return (
        user.is_superuser
        or getattr(user, "role", None) == "ADMIN"
        or getattr(user, "position", None) == "ADMIN"
    )


def is_finance(user):
    return getattr(user, "role", None) in ["FINANCE_MANAGER", "ACCOUNTANT"]


def is_store_manager(user):
    return getattr(user, "role", None) == "STORE_MANAGER"


class IsAdminOrFinance(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (
            is_admin(request.user) or is_finance(request.user)
        )


class IsStoreManager(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and is_store_manager(request.user)


class IsAdminOnly(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and is_admin(request.user)