# from rest_framework import generics
# from rest_framework.response import Response
# from django.db import connection
# from customers.models import Client, User # Import your tenant model
# from .serializers import StoreSerializer
# from rest_framework import status, viewsets
# from rest_framework.decorators import action
# from .models import Store, Employee
# from django.db import transaction
# from rest_framework import permissions
# from rest_framework.permissions import IsAuthenticated

# class IsAdminUser(permissions.BasePermission):
#     def has_permission(self, request, view):
#         return request.user.is_authenticated and request.user.position == 'Admin'


#     @action(detail=True, methods=['post'])
#     def add_staff(self, request, pk=None):
#         """Assign or reassign one or more users to a store."""
#         store = Store.objects.get(id=pk)
#         usernames = request.data.get('usernames', [])  # List of usernames
#         position = request.data.get('position')  # Position (Manager, Cashier, etc.)

#         if not usernames:
#             return Response({"error": "No usernames provided"}, status=status.HTTP_400_BAD_REQUEST)

#         # Ensure store has only one manager
#         if position == 'Manager' and Employee.objects.filter(store=store, user__position='Manager').exists():
#             return Response({"error": "This store already has a manager."}, status=status.HTTP_400_BAD_REQUEST)

#         # Process each user to assign or reassign to the store
#         with transaction.atomic():
#             for username in usernames:
#                 try:
#                     user = User.objects.get(username=username)
#                 except User.DoesNotExist:
#                     return Response({"error": f"User {username} not found"}, status=status.HTTP_404_NOT_FOUND)

#                 # Check if the user is already assigned to any store
#                 existing_employee = Employee.objects.filter(user=user, store=store).first()
#                 if existing_employee:
#                     # User is already assigned to the store, so just update their record if needed
#                     existing_employee.save()  # Reassign logic (could add more fields to modify)
#                 else:
#                     # If the user was assigned to another store, remove them from that store first
#                     if Employee.objects.filter(user=user).exists():
#                         # Remove the user from any store they were previously assigned to
#                         old_store_employee = Employee.objects.filter(user=user).first()
#                         old_store_employee.delete()  # Remove the previous assignment
                    
#                     # Assign the user to the new store
#                     Employee.objects.create(user=user, store=store)

#         return Response({"message": "Users have been assigned or reassigned to the store."}, status=status.HTTP_200_OK)
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from django.db import transaction, connection
from customers.models import Client, User
from .models import Store, Employee
from .serializers import StoreSerializer
from rest_framework import permissions

class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.position == 'Admin'

class IsStoreAssigned(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.position == 'Admin':
            return True
        return Employee.objects.filter(user=request.user, store=obj).exists()
# permission_classes = [IsAuthenticated, IsStoreAssigned]

class StoreViewSet(viewsets.ModelViewSet):
    queryset = Store.objects.all()
    serializer_class = StoreSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        user = self.request.user

        if user.position == 'Admin':
            return Store.objects.all()  # Admin can access all stores in the tenant
        else:
            # Get stores the user is assigned to
            return Store.objects.filter(employee__user=user)
        
    # Custom store creation with domain assignment
    @action(detail=False, methods=['post'], url_path='create-store')
    def create_store(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            schema_name = connection.schema_name
            try:
                tenant = Client.objects.get(schema_name=schema_name)
                tenant_domain = tenant.get_domain()

                if tenant_domain:
                    store = serializer.save()
                    store.domain_name = f"{store.store_name.lower()}.{tenant_domain}"
                    store.save()
                    return Response(self.get_serializer(store).data, status=status.HTTP_201_CREATED)
                else:
                    return Response({"error": "No domain found for tenant"}, status=status.HTTP_400_BAD_REQUEST)
            except Client.DoesNotExist:
                return Response({"error": "Tenant not found"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Add or reassign staff
    # @action(detail=True, methods=['post'], url_path='add-staff')
    # def add_staff(self, request, pk=None):
    #     try:
    #         store = self.get_object()
    #     except Store.DoesNotExist:
    #         return Response({"error": "Store not found"}, status=status.HTTP_404_NOT_FOUND)

    #     usernames = request.data.get('usernames', [])
    #     position = request.data.get('position')

    #     if not usernames:
    #         return Response({"error": "No usernames provided"}, status=status.HTTP_400_BAD_REQUEST)

    #     if position == 'Manager' and Employee.objects.filter(store=store, user__position='Manager').exists():
    #         return Response({"error": "This store already has a manager."}, status=status.HTTP_400_BAD_REQUEST)

    #     with transaction.atomic():
    #         for username in usernames:
    #             try:
    #                 user = User.objects.get(username=username)
    #             except User.DoesNotExist:
    #                 return Response({"error": f"User {username} not found"}, status=status.HTTP_404_NOT_FOUND)

    #             existing_employee = Employee.objects.filter(user=user, store=store).first()
    #             if existing_employee:
    #                 existing_employee.position = position
    #                 existing_employee.save()
    #             else:
    #                 Employee.objects.filter(user=user).delete()
    #                 Employee.objects.create(user=user, store=store, position=position)

    #     return Response({"message": "Users have been assigned or reassigned to the store."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='add-staff')
    def add_staff(self, request, pk=None):
        """Assign or reassign a single user to a store."""
        store = Store.objects.get(id=pk)
        username = request.data.get('username')  # Single username
        if not username:
            return Response({"error": "Username is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({"error": f"User '{username}' not found"}, status=status.HTTP_404_NOT_FOUND)

        # Prevent multiple managers in a store
        if user.position == 'Manager' and Employee.objects.filter(store=store, user__position='Manager').exists():
            return Response({"error": "This store already has a manager."}, status=status.HTTP_400_BAD_REQUEST)

        # Reassign logic
        with transaction.atomic():
            existing_employee = Employee.objects.filter(user=user).first()
            if existing_employee:
                existing_employee.delete()  # Remove from old store

            Employee.objects.create(user=user, store=store)

        return Response({"message": f"User '{username}' has been assigned to the store."}, status=status.HTTP_200_OK)

    # # Update logic (optional customization, or rely on ModelViewSet's default)
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)
