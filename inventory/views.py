from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .models import Warehouse, Section, Inventory, TransferLog, StockRequest, ProductLot, Product, Transfer
from stores.models import Store
from payroll.models import Employee
from .serializers import (WarehouseSerializer, SectionSerializer, TransferSerializer, StockRequestSerializer, 
                AddInventorySerializer, InventorySerializer)
from inventory.models import (
    Supplier,
    Purchase,
    InventoryMovement
)

from inventory.serializers import (
    SupplierSerializer,
    PurchaseSerializer,
    InventoryMovementSerializer
)

from inventory.services.purchase_posting import (
    PurchasePostingService
)

from inventory.services.sales_posting import (
    SalesPostingService
)
from django.db import transaction, models
from collections import defaultdict

class IsStoreAssigned(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.position == 'Admin':
            return True
        return Employee.objects.filter(user=request.user, store=obj).exists()
    
# Warehouse Viewset
class WarehouseViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['get'], url_path='list')
    def list_warehouses(self, request):
        warehouses = Warehouse.objects.filter(tenant=request.user.client)
        serializer = WarehouseSerializer(warehouses, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='create')
    def create_warehouse(self, request):
        serializer = WarehouseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['put'], url_path='update')
    def update_warehouse(self, request, pk=None):
        warehouse = self.get_object()
        serializer = WarehouseSerializer(warehouse, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'], url_path='delete')
    def delete_warehouse(self, request, pk=None):
        warehouse = self.get_object()
        warehouse.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

#Section Viewset
class SectionViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['get'], url_path='list')
    def list_sections(self, request):
        warehouse = request.query_params.get('warehouse', None)
        if warehouse:
            sections = Section.objects.filter(warehouse=warehouse)
        else:
            sections = Section.objects.all()
        serializer = SectionSerializer(sections, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='create')
    def create_section(self, request):
        serializer = SectionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['put'], url_path='update')
    def update_section(self, request, pk=None):
        section = self.get_object()
        serializer = SectionSerializer(section, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'], url_path='delete')
    def delete_section(self, request, pk=None):
        section = self.get_object()
        section.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


#Transfer Viewset (considering Lot for FIFO during transfer)
class TransferViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['get'], url_path='list')
    def list_transfers(self, request):
        transfers = Transfer.objects.filter(tenant=request.user.client)
        serializer = TransferSerializer(transfers, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['put'], url_path='update')
    def update_transfer(self, request, pk=None):
        transfer = self.get_object()
        serializer = TransferSerializer(transfer, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'], url_path='delete')
    def delete_transfer(self, request, pk=None):
        transfer = self.get_object()
        transfer.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='execute')
    @transaction.atomic
    def execute_transfer(self, request, pk=None):

        try:

            transfer = self.get_object()

            if transfer.status != 'pending':
                return Response(
                    {"status": "Transfer is not pending."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            from_inventory = (
                Inventory.objects.filter(
                    warehouse=transfer.source_warehouse,
                    product=transfer.product
                )
                .select_related(
                    'lot',
                    'product_variant'
                )
                .order_by('lot__purchase_date')
            )

            quantity_left = transfer.quantity

            for inventory in from_inventory:

                if quantity_left <= 0:
                    break

                if inventory.quantity <= quantity_left:

                    deducted_qty = inventory.quantity

                else:

                    deducted_qty = quantity_left

                # -----------------------------------
                # DEDUCT SOURCE INVENTORY
                # -----------------------------------

                inventory.deduct_quantity(
                    deducted_qty
                )

                quantity_left -= deducted_qty

                # -----------------------------------
                # CREATE/UPDATE DESTINATION INVENTORY
                # -----------------------------------

                destination_inventory, created = (
                    Inventory.objects.get_or_create(
                        tenant=transfer.source_warehouse.tenant,
                        warehouse=transfer.destination_warehouse,
                        section=transfer.destination_warehouse.sections.first(),
                        product=transfer.product,
                        product_variant=inventory.product_variant,
                        lot=inventory.lot,
                        defaults={
                            'quantity': deducted_qty
                        }
                    )
                )

                if not created:

                    destination_inventory.quantity += deducted_qty

                    destination_inventory.save(
                        update_fields=[
                            'quantity',
                            'updated_at'
                        ]
                    )

                # -----------------------------------
                # TRANSFER OUT MOVEMENT
                # -----------------------------------

                InventoryMovement.objects.create(
                    tenant=transfer.source_warehouse.tenant,
                    warehouse=transfer.source_warehouse,
                    product=transfer.product,
                    product_variant=inventory.product_variant,
                    lot=inventory.lot,
                    transfer=transfer,
                    movement_type='TRANSFER_OUT',
                    quantity=deducted_qty,
                    unit_cost=inventory.lot.purchase_price,
                    total_cost=(
                        deducted_qty
                        * inventory.lot.purchase_price
                    ),
                    reference=f'TRF-{transfer.id}',
                    remarks='Transfer Out'
                )

                # -----------------------------------
                # TRANSFER IN MOVEMENT
                # -----------------------------------

                InventoryMovement.objects.create(
                    tenant=transfer.destination_warehouse.tenant,
                    warehouse=transfer.destination_warehouse,
                    product=transfer.product,
                    product_variant=inventory.product_variant,
                    lot=inventory.lot,
                    transfer=transfer,
                    movement_type='TRANSFER_IN',
                    quantity=deducted_qty,
                    unit_cost=inventory.lot.purchase_price,
                    total_cost=(
                        deducted_qty
                        * inventory.lot.purchase_price
                    ),
                    reference=f'TRF-{transfer.id}',
                    remarks='Transfer In'
                )

            transfer.status = 'completed'
            transfer.confirmed_by = request.user
            transfer.save()

            return Response({
                "status": "Transfer executed successfully."
            })

        except Exception as e:

            return Response(
                {"status": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class StockRequestViewSet(viewsets.ViewSet):
    
    @action(detail=False, methods=['get'], url_path='list')
    def list_requests(self, request):
        # Get the filter parameters (status, product, etc.)
        status_filter = request.query_params.get('status', None)  # Optionally filter by status
        product_filter = request.query_params.get('product', None)  # Optionally filter by product ID

        # Start with a base queryset, ordering by status to show 'pending' requests first
        stock_requests = StockRequest.objects.all().order_by('-status', 'created_at')  # Prioritize 'pending' first
        
        # Apply filters if provided
        if status_filter:
            stock_requests = stock_requests.filter(status=status_filter)
        
        if product_filter:
            stock_requests = stock_requests.filter(product__id=product_filter)

        # Serialize the filtered stock requests
        serializer = StockRequestSerializer(stock_requests, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='create')
    def create_request(self, request):
        # Get lot_id and quantity_requested from the request body
        lot_id = request.data.get('lot_id')
        quantity_requested = request.data.get('quantity_requested')

        # Check if necessary fields are provided
        if not lot_id or quantity_requested is None or quantity_requested <= 0:
            return Response({"error": "lot_id and a positive quantity_requested are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Get the lot and store
            lot = ProductLot.objects.get(id=lot_id)
            store = Store.objects.get(id=request.user.store.id)  # Assuming store is linked to the user
        except ProductLot.DoesNotExist:
            return Response({"error": "Lot not found"}, status=status.HTTP_404_NOT_FOUND)
        except Store.DoesNotExist:
            return Response({"error": "Store not found"}, status=status.HTTP_404_NOT_FOUND)

        # Check the store's inventory to see if there is enough stock for the requested product
        store_inventory = Inventory.objects.filter(warehouse=store.warehouse, product=lot.product).order_by('lot__purchase_date')

        quantity_left = quantity_requested
        for inventory in store_inventory:
            if quantity_left <= 0:
                break

            # Deduct stock from inventory (FIFO logic)
            if inventory.quantity <= quantity_left:
                quantity_left -= inventory.quantity
            else:
                quantity_left = 0

        # If there is any quantity left (shortfall), create a stock request
        if quantity_left > 0:
            shortfall = quantity_left
            stock_request = StockRequest(
                store=store,
                product=lot.product,
                quantity_requested=shortfall,
                status="pending"  # Status is pending until confirmation
            )

            # Validate the serializer with the stock request data
            serializer = StockRequestSerializer(stock_request)
            
            # Check if the serializer is valid
            if serializer.is_valid():
                # Save the stock request and return the serialized data
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                # If the serializer is not valid, return the errors
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # If there is enough stock, inform the user
        return Response({"message": "There is enough stock available in the store warehouse."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['put'], url_path='update')
    def update_request(self, request, pk=None):
        # Retrieve the stock request object
        stock_request = self.get_object()

        # Check if the stock request status is 'pending'
        if stock_request.status != 'pending':
            return Response({"error": "You can only update a stock request if its status is 'pending'."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Proceed with updating the stock request if it's 'pending'
        serializer = StockRequestSerializer(stock_request, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'], url_path='delete')
    def delete_request(self, request, pk=None):
        # Retrieve the stock request object
        stock_request = self.get_object()

        # Check if the stock request status is 'pending'
        if stock_request.status != 'pending':
            return Response({"error": "You can only delete a stock request if its status is 'pending'."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Proceed with deleting the stock request if it's 'pending'
        stock_request.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='confirm')
    def confirm_stock_request(self, request, pk=None):
        stock_request = self.get_object()
        
        # Confirm only if status is pending
        if stock_request.status != 'pending':
            return Response({"error": "Only pending requests can be confirmed."}, status=status.HTTP_400_BAD_REQUEST)

         # Create a transfer once the stock request is confirmed
        source_warehouse = Warehouse.objects.get(type='general')  # Assuming 'general' is the central warehouse
        destination_warehouse = stock_request.store.warehouse

        transfer = Transfer.objects.create(
            source_warehouse=source_warehouse,
            destination_warehouse=destination_warehouse,
            product=stock_request.product,
            quantity=stock_request.quantity_requested,
            status='pending'  # The transfer is initially in a pending state
        )
        stock_request.status = 'approved'
        stock_request.save()
        
        return Response({
            "status": "Stock request confirmed and transfer created.",
            "transfer": TransferSerializer(transfer).data
        })
class SupplierViewSet(viewsets.ModelViewSet):

    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Supplier.objects.filter(
            tenant=self.request.tenant
        )

    def perform_create(self, serializer):
        serializer.save(
            tenant=self.request.tenant
        )


class PurchaseViewSet(viewsets.ModelViewSet):

    serializer_class = PurchaseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Purchase.objects
            .filter(tenant=self.request.tenant)
            .prefetch_related("items")
            .select_related("supplier", "store_name")
        )

    def perform_create(self, serializer):
        serializer.save(
            tenant=self.request.tenant
        )

    @action(detail=True, methods=["post"], url_path="post")
    def post_purchase(self, request, pk=None):
        purchase = self.get_object()

        try:
            PurchasePostingService.post_purchase(
                purchase.id,
                user=request.user
            )

            return Response(
                {"message": "Purchase posted successfully."},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class InventoryMovementViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = InventoryMovementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = (
            InventoryMovement.objects
            .filter(tenant=self.request.tenant)
            .select_related("product", "warehouse", "lot")
            .order_by("-created_at")
        )

        movement_type = self.request.query_params.get("movement_type")

        if movement_type:
            queryset = queryset.filter(movement_type=movement_type)

        return queryset
