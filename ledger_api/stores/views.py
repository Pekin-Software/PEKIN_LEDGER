# from django.shortcuts import render

# # Create your views here.
# class StoreViewSet(viewsets.ModelViewSet):
#     queryset = Store.objects.all()
#     serializer_class = StoreSerializer

# class StoreProductViewSet(viewsets.ModelViewSet):
#     queryset = StoreProduct.objects.all()
#     serializer_class = StoreProductSerializer
# from rest_framework import viewsets
# from rest_framework.response import Response
# from rest_framework import status
# from .models import Store
# from .serializers import StoreSerializer
# from customers.models import Client

# class StoreViewSet(viewsets.ModelViewSet):
#     queryset = Store.objects.all()
#     serializer_class = StoreSerializer

#     def create(self, request, *args, **kwargs):
#         """
#         Override the create method to handle store creation and 
#         automatically set the domain based on the tenant's domain.
#         """
#         # Ensure tenant is provided in the request
#         tenant = request.data.get('tenant')
#         if not tenant:
#             return Response({"detail": "Tenant is required"}, status=status.HTTP_400_BAD_REQUEST)
        
#         # Validate tenant ID or retrieve tenant object (assuming tenant is passed as ID)
#         try:
#             tenant_instance = Client.objects.get(id=tenant)
#         except Client.DoesNotExist:
#             return Response({"detail": "Invalid tenant ID"}, status=status.HTTP_400_BAD_REQUEST)

#         # Attach tenant instance to the request data and create the store
#         request.data['tenant'] = tenant_instance.id
#         return super().create(request, *args, **kwargs)

from rest_framework import generics
from rest_framework.response import Response
from django.db import connection
from customers.models import Client, User # Import your tenant model
from .serializers import StoreSerializer
from customers.serializers import UserSerializer
from rest_framework import status, viewsets
from rest_framework.decorators import action
from .models import Store, Employee
from django.db import transaction

class StoreCreateView(generics.CreateAPIView):
    queryset = Store.objects.all()
    serializer_class = StoreSerializer
    # permission_classes = [IsAuthenticated]  # Uncomment if you want authentication

    def perform_create(self, serializer):
        schema_name = connection.schema_name  # Get the current tenant schema
        try:
            tenant = Client.objects.get(schema_name=schema_name)  # Find the tenant
            tenant_domain = tenant.get_domain()  # Fetch the actual domain

            if tenant_domain:  # Ensure a domain exists before assigning
                store = serializer.save()
                store.domain_name = f"{store.store_name.lower()}.{tenant_domain}"  # Assign domain dynamically
                store.save()
            else:
                return Response({"error": "No domain found for tenant"}, status=400)
                
        except Client.DoesNotExist:
            return Response({"error": "Tenant not found"}, status=400)
class StoreEmployeeViewSet(viewsets.ViewSet):
    
    @action(detail=True, methods=['post'])
    def add_staff(self, request, pk=None):
        """Assign or reassign one or more users to a store."""
        store = Store.objects.get(id=pk)
        usernames = request.data.get('usernames', [])  # List of usernames
        position = request.data.get('position')  # Position (Manager, Cashier, etc.)

        if not usernames:
            return Response({"error": "No usernames provided"}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure store has only one manager
        if position == 'Manager' and Employee.objects.filter(store=store, user__position='Manager').exists():
            return Response({"error": "This store already has a manager."}, status=status.HTTP_400_BAD_REQUEST)

        # Process each user to assign or reassign to the store
        with transaction.atomic():
            for username in usernames:
                try:
                    user = User.objects.get(username=username)
                except User.DoesNotExist:
                    return Response({"error": f"User {username} not found"}, status=status.HTTP_404_NOT_FOUND)

                # Check if the user is already assigned to any store
                existing_employee = Employee.objects.filter(user=user, store=store).first()
                if existing_employee:
                    # User is already assigned to the store, so just update their record if needed
                    existing_employee.save()  # Reassign logic (could add more fields to modify)
                else:
                    # If the user was assigned to another store, remove them from that store first
                    if Employee.objects.filter(user=user).exists():
                        # Remove the user from any store they were previously assigned to
                        old_store_employee = Employee.objects.filter(user=user).first()
                        old_store_employee.delete()  # Remove the previous assignment
                    
                    # Assign the user to the new store
                    Employee.objects.create(user=user, store=store)

        return Response({"message": "Users have been assigned or reassigned to the store."}, status=status.HTTP_200_OK)



