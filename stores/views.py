from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from django.db import transaction, connection
from customers.models import Client, User
from customers.serializers import UserSerializer, StaffSerializer
from .models import Store, Employee
from inventory.models import Inventory, Warehouse
from .serializers import StoreSerializer, AddInventorySerializer, InventoryForStoreSerializer
from rest_framework import permissions
from django.db.models import Sum, Max, F, OuterRef, Subquery
class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.position == 'Admin'

class IsStoreAssigned(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.position == 'Admin':
            return True
        return Employee.objects.filter(user=request.user, store=obj).exists()

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

        # List staff assigned to a store
    
    @action(detail=True, methods=['get'], url_path='list-staff')
    def list_staff(self, request, pk=None):
        try:
            store = Store.objects.get(pk=pk)
        except Store.DoesNotExist:
            return Response({"error": "Store not found"}, status=status.HTTP_404_NOT_FOUND)

        employees = Employee.objects.filter(store=store).select_related('user')
        staff_users = [e.user for e in employees]
        serializer = StaffSerializer(staff_users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # Remove a user from a store
    @action(detail=True, methods=['delete'], url_path='remove-staff')
    def remove_staff(self, request, pk=None):
        username = request.data.get('username')
        if not username:
            return Response({"error": "Username is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            store = Store.objects.get(pk=pk)
            user = User.objects.get(username=username)
            employee = Employee.objects.get(user=user, store=store)
        except Store.DoesNotExist:
            return Response({"error": "Store not found"}, status=status.HTTP_404_NOT_FOUND)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        except Employee.DoesNotExist:
            return Response({"error": "User is not assigned to this store"}, status=status.HTTP_400_BAD_REQUEST)

        employee.delete()
        return Response({"message": f"User '{username}' has been removed from the store."}, status=status.HTTP_200_OK)
    

    # Add inventory (admin only)
    # @action(detail=True, methods=['post'], url_path='add-inventory', permission_classes=[IsAdminUser])
    # def add_inventory(self, request, pk=None):
    #     try:
    #         store = Store.objects.get(pk=pk)
    #     except Store.DoesNotExist:
    #         return Response({"error": "Store not found in this tenant."}, status=status.HTTP_404_NOT_FOUND)

    #     warehouse = store.warehouses.first()
    #     if not warehouse:
    #         return Response({"error": "Store has no warehouse."}, status=status.HTTP_400_BAD_REQUEST)

    #     # Prepare and validate inventory data without trusting store_id from client
    #     serializer = AddInventorySerializer(
    #         data=request.data,
    #         context={'request': request, 'store': store, 'warehouse': warehouse}
    #     )
    #     serializer.is_valid(raise_exception=True)

    #     serializer.save()

    #     return Response({'message': 'Inventory added/updated successfully.'}, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'], url_path='add-inventory', permission_classes=[IsAdminUser])
    def add_inventory(self, request, pk=None):
        try:
            store = Store.objects.get(pk=pk)
        except Store.DoesNotExist:
            return Response({"error": "Store not found in this tenant."}, status=status.HTTP_404_NOT_FOUND)

        store_warehouse = store.warehouses.first()
        if not store_warehouse:
            return Response({"error": "Store has no warehouse."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate incoming data using serializer
        serializer = AddInventorySerializer(data=request.data, context={'request': request, 'store': store, 'warehouse': store_warehouse})
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        # Find general warehouse for this tenant
        general_warehouse = Warehouse.objects.filter(tenant=store.tenant, warehouse_type='general').first()
        if not general_warehouse:
            return Response({"error": "General warehouse not found for this tenant."}, status=status.HTTP_400_BAD_REQUEST)

        # Find inventory in general warehouse
        try:
            general_inventory = Inventory.objects.get(
                warehouse=general_warehouse,
                product=validated_data['product'],
                lot=validated_data['lot'],
                tenant=store.tenant
            )
        except Inventory.DoesNotExist:
            return Response({"error": "Inventory not found in general warehouse."}, status=status.HTTP_404_NOT_FOUND)

        try:
            # Allocate stock from general warehouse to store warehouse
            allocated_inventory = general_inventory.allocate_to_store(store_warehouse, validated_data['quantity'])
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'message': 'Stock allocated to store successfully.',
            'allocated_quantity': validated_data['quantity'],
            'store_inventory_id': allocated_inventory.id
        }, status=status.HTTP_200_OK)

    #return product from a store 
    @action(detail=True, methods=['post'], url_path='return-inventory', permission_classes=[IsAdminUser])
    def return_from_store(self, request, pk=None):
        try:
            store = Store.objects.get(pk=pk)
        except Store.DoesNotExist:
            return Response({"error": "Store not found."}, status=status.HTTP_404_NOT_FOUND)

        store_warehouse = store.warehouses.first()
        if not store_warehouse:
            return Response({"error": "Store has no warehouse."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate input data: expect product_id, lot_id, quantity
        product_id = request.data.get('product_id')
        lot_id = request.data.get('lot_id')
        quantity = request.data.get('quantity')

        if not product_id or not lot_id or not quantity:
            return Response({"error": "product_id, lot_id, and quantity are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            quantity = int(quantity)
            if quantity < 1:
                raise ValueError
        except ValueError:
            return Response({"error": "Quantity must be a positive integer."}, status=status.HTTP_400_BAD_REQUEST)

        # Find the general warehouse
        general_warehouse = Warehouse.objects.filter(tenant=store.tenant, warehouse_type='general').first()
        if not general_warehouse:
            return Response({"error": "General warehouse not found."}, status=status.HTTP_400_BAD_REQUEST)

        # Get general inventory entry
        try:
            general_inventory = Inventory.objects.get(
                warehouse=general_warehouse,
                product_id=product_id,
                lot_id=lot_id,
                tenant=store.tenant
            )
        except Inventory.DoesNotExist:
            return Response({"error": "Inventory not found in general warehouse."}, status=status.HTTP_404_NOT_FOUND)

        try:
            # Use the return_from_store method to return stock from store to general warehouse
            store_inventory = general_inventory.return_from_store(store_warehouse, quantity)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message": "Stock returned from store successfully.",
            "returned_quantity": quantity,
            "store_inventory_id": store_inventory.id
        }, status=status.HTTP_200_OK)
    
    # List inventory for a store (admin or assigned users)
    # @action(detail=True, methods=['get'], url_path='inventory', permission_classes=[IsAuthenticated, IsStoreAssigned])
    # def list_inventory(self, request, pk=None):
    #     try:
    #         store = Store.objects.get(pk=pk)
    #     except Store.DoesNotExist:
    #         return Response({"error": "Store not found in this tenant."}, status=status.HTTP_404_NOT_FOUND)

    #     self.check_object_permissions(request, store)  # Enforce IsStoreAssigned

    #     warehouse = store.warehouses.first()
    #     if not warehouse:
    #         return Response({"error": "Warehouse for this store not found."}, status=status.HTTP_404_NOT_FOUND)

    #     inventory_qs = Inventory.objects.filter(warehouse=warehouse)
    #     serializer = InventoryForStoreSerializer(inventory_qs, many=True, context={'request': request})
    #     return Response(serializer.data, status=status.HTTP_200_OK)

    from django.db.models import Max, Sum, F, Subquery, OuterRef

    @action(detail=True, methods=['get'], url_path='inventory', permission_classes=[IsAuthenticated, IsStoreAssigned])
    def list_inventory(self, request, pk=None):
        try:
            store = Store.objects.get(pk=pk)
        except Store.DoesNotExist:
            return Response({"error": "Store not found in this tenant."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, store)

        # Get all warehouses for this store
        store_warehouses = store.warehouses.all()
        if not store_warehouses.exists():
            return Response({"error": "No warehouse found for this store."}, status=status.HTTP_404_NOT_FOUND)

        # Filter inventory for store warehouses
        store_inventory = Inventory.objects.filter(warehouse__in=store_warehouses)

        # Total quantity per product in the store
        qty_map = (
            store_inventory.values('product_id')
            .annotate(total_qty=Sum('quantity'))
        )
        qty_map = {item['product_id']: item['total_qty'] for item in qty_map}

        # Get the newest lot per product in the store (by SKU)
        latest_inventory_subquery = store_inventory.filter(
            product=OuterRef('product')
        ).order_by('-lot__sku')

        latest_inventory_per_product = (
            store_inventory
            .values('product_id')
            .annotate(
                latest_inventory_id=Subquery(
                    latest_inventory_subquery.values('id')[:1]
                )
            )
            .values_list('latest_inventory_id', flat=True)
        )

        # Final queryset with only one latest inventory per product
        latest_inventories = Inventory.objects.filter(id__in=latest_inventory_per_product).select_related('product', 'lot')

        serializer = InventoryForStoreSerializer(
            latest_inventories,
            many=True,
            context={
                'request': request,
                'qty_map': qty_map,
                'inventory_qs': store_inventory  # Pass full inventory for correct lot filtering in nested serializer
            }
        )

        return Response(serializer.data, status=status.HTTP_200_OK)


    #List Main Inventory
    @action(detail=False, methods=['get'], url_path='main-inventory', permission_classes=[IsAuthenticated])
    def main_inventory(self, request):
        client = request.user.domain

        warehouse = Warehouse.objects.filter(
            tenant=client,
            warehouse_type='general'
        ).first()

        if not warehouse:
            return Response({"error": "General warehouse not found."}, status=status.HTTP_404_NOT_FOUND)

        # All inventory across all warehouses for total calculation
        all_inventory_qs = Inventory.objects.filter(product__tenant=client)

        # Inventory from the main warehouse (for display)
        main_inventory_qs = Inventory.objects.filter(warehouse=warehouse)

        # Calculate total quantity per product
        total_qty_map = (
        all_inventory_qs
        .values('product_id')
        .annotate(total_qty=Sum('quantity'))
        )

        qty_map = {item['product_id']: item['total_qty'] for item in total_qty_map}

        # Pass qty_map to serializer context so serializer can use it
        serializer = InventoryForStoreSerializer(
        main_inventory_qs.distinct('product_id'),  # show products from main warehouse only
        many=True,
        context={
            'request': request,
            'inventory_qs': all_inventory_qs,  # so product.lots can access all lots across locations
            'qty_map': qty_map
            }
        )

        return Response(serializer.data, status=status.HTTP_200_OK)

    #Overview for Inventory
    @action(detail=False, methods=['get'], url_path='overview', permission_classes=[IsAuthenticated])
    def overview(self, request):
        client = request.user.domain

        # Filter inventories for this tenant only
        queryset = Inventory.objects.select_related('product', 'warehouse', 'lot').filter(
            product__tenant=client
        )

        all_inventories = list(queryset)
        first_item_id = all_inventories[0].id if all_inventories else None

        # Compute total quantity per product
        total_qty_map = (
            queryset
            .values('product_id')
            .annotate(total_qty=Sum('quantity'))
        )
        qty_map = {item['product_id']: item['total_qty'] for item in total_qty_map}

        serializer = InventoryForStoreSerializer(
            all_inventories,
            many=True,
            context={
                'request': request,
                'qty_map': qty_map,
                'include_overview': True,
                'all_inventories': all_inventories,
                'first_item_id': first_item_id,
            }
        )

        return Response({
            "overview": serializer.data[0].get("overview") if serializer.data else {},
        })



