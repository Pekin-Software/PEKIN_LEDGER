# # from django.shortcuts import render

# # # Create your views here.
# # class CategoryViewSet(viewsets.ModelViewSet):
# #     queryset = Category.objects.all()
# #     serializer_class = CategorySerializer

# # class ProductViewSet(viewsets.ModelViewSet):
# #     queryset = Product.objects.all()
# #     serializer_class = ProductSerializer

# #     @action(detail=True, methods=['get'])
# #     def flattened(self, request, pk=None):
# #         product = self.get_object()
# #         serializer = ProductSerializer(product)
        
# #         # Get the attributes in a flattened format
# #         attributes = serializer.data['attributes']
# #         flattened_data = {
# #             'SKU': product.sku,
# #             'Product Name': product.name,
# #             **attributes  # Add the dynamic attributes to the flattened structure
# #         }

# #         return Response(flattened_data)

# # class WarehouseViewSet(viewsets.ModelViewSet):
# #     queryset = Warehouse.objects.all()
# #     serializer_class = WarehouseSerializer
# #     filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
# #     filterset_fields = ['sections__name', 'products__category', 'products__expiration_date', 'products__created_at', 'products__updated_at', 'products__price']
# #     ordering_fields = ['name', 'location']
# #     permission_classes = [permissions.IsAdminUser]  # Only admins can manage warehouses

# #     @action(detail=False, methods=['post'], permission_classes=[permissions.IsAdminUser], url_path='create')
# #     def create_warehouse(self, request):
# #         """ Create a new warehouse """
# #         serializer = self.get_serializer(data=request.data)
# #         if serializer.is_valid():
# #             serializer.save()
# #             return Response(serializer.data, status=201)
# #         return Response(serializer.errors, status=400)

# #     @action(detail=True, methods=['put', 'patch'], permission_classes=[permissions.IsAdminUser], url_path='update')
# #     def update_warehouse(self, request, pk=None):
# #         """ Update an existing warehouse """
# #         warehouse = self.get_object()
# #         serializer = self.get_serializer(warehouse, data=request.data, partial=True)
# #         if serializer.is_valid():
# #             serializer.save()
# #             return Response(serializer.data)
# #         return Response(serializer.errors, status=400)

# #     @action(detail=True, methods=['delete'], permission_classes=[permissions.IsAdminUser], url_path='delete')
# #     def delete_warehouse(self, request, pk=None):
# #         """ Delete a warehouse """
# #         warehouse = self.get_object()
# #         warehouse.delete()
# #         return Response(status=204)

# #     @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated], url_path='list-warehouse')
# #     def list_warehouse(self, request):
# #         """ List all warehouses """
# #         warehouses = self.get_queryset()
# #         serializer = self.get_serializer(warehouses, many=True)
# #         return Response(serializer.data)

# #     @action(detail=True, methods=['get'], permission_classes=[IsAdminOrManager], url_path='product-list')
# #     def product_list(self, request, pk=None):
# #         """ List all products in a specific warehouse with filtering options """
# #         warehouse = self.get_object()
# #         products = Product.objects.filter(section__warehouse=warehouse)
# #         section = request.query_params.get('section')
# #         category = request.query_params.get('category')
# #         expiration_date = request.query_params.get('expiration_date')
# #         created_at = request.query_params.get('created_at')
# #         updated_at = request.query_params.get('updated_at')
# #         price = request.query_params.get('price')

# #         if section:
# #             products = products.filter(section__name=section)
# #         if category:
# #             products = products.filter(category=category)
# #         if expiration_date:
# #             products = products.filter(expiration_date=expiration_date)
# #         if created_at:
# #             products = products.filter(created_at=created_at)
# #         if updated_at:
# #             products = products.filter(updated_at=updated_at)
# #         if price:
# #             products = products.filter(price=price)

# #         serializer = ProductSerializer(products, many=True)
# #         return Response(serializer.data)

# # class SectionViewSet(viewsets.ModelViewSet):
# #     queryset = Section.objects.all()
# #     serializer_class = SectionSerializer
# #     permission_classes = [permissions.IsAdminUser]  # Only admins can manage sections

# #     @action(detail=False, methods=['post'], permission_classes=[permissions.IsAdminUser], url_path='create')
# #     def create_section(self, request):
# #         """ Create a new section """
# #         serializer = self.get_serializer(data=request.data)
# #         if serializer.is_valid():
# #             serializer.save()
# #             return Response(serializer.data, status=201)
# #         return Response(serializer.errors, status=400)

# #     @action(detail=True, methods=['put', 'patch'], permission_classes=[permissions.IsAdminUser], url_path='update')
# #     def update_section(self, request, pk=None):
# #         """ Update an existing section """
# #         section = self.get_object()
# #         serializer = self.get_serializer(section, data=request.data, partial=True)
# #         if serializer.is_valid():
# #             serializer.save()
# #             return Response(serializer.data)
# #         return Response(serializer.errors, status=400)

# #     @action(detail=True, methods=['delete'], permission_classes=[permissions.IsAdminUser], url_path='delete')
# #     def delete_section(self, request, pk=None):
# #         """ Delete a section """
# #         section = self.get_object()
# #         section.delete()
# #         return Response(status=204)


from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter
from .models import Warehouse, Section, Inventory, Transfer, StockRequest, Lot, Product, Store
from .serializers import WarehouseSerializer, SectionSerializer, InventorySerializer, TransferSerializer, StockRequestSerializer, LotSerializer
from django.db.models import Q 

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

#Inventory Viewset (using Lot for FIFO)
class InventoryViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['get'], url_path='list')
    def list_inventory(self, request):
        inventory = Inventory.objects.filter(store=request.user.store)
        serializer = InventorySerializer(inventory, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='add-stock')
    def add_stock(self, request):
        # Extracting data from the request
        product_id = request.data.get("product")
        lot_id = request.data.get("lot")
        warehouse_id = request.data.get("warehouse")
        section_id = request.data.get("section")
        quantity = request.data.get("quantity")
        
        # Retrieve the necessary objects
        try:
            product = Product.objects.get(id=product_id)
            lot = Lot.objects.get(id=lot_id)
            warehouse = Warehouse.objects.get(id=warehouse_id)
            section = Section.objects.get(id=section_id)
        except (Product.DoesNotExist, Lot.DoesNotExist, Warehouse.DoesNotExist, Section.DoesNotExist):
            return Response({"error": "Invalid product, lot, warehouse, or section ID."}, status=status.HTTP_400_BAD_REQUEST)
        
        store = request.user.store
        tenant = request.user.client
        
        # Check if inventory exists and update, or create new one
        try:
            # Check if the inventory record already exists for the given lot and product
            inventory = Inventory.objects.get(product=product, lot=lot, warehouse=warehouse, section=section)
            # If found, simply add quantity to the existing record
            inventory.add_quantity(quantity)
        except Inventory.DoesNotExist:
            # If no existing record, create a new inventory record
            Inventory.objects.create(
                product=product,
                lot=lot,
                warehouse=warehouse,
                section=section,
                quantity=quantity,
                store=store,
                tenant=tenant
            )

        # If everything went well, return success response
        return Response({"message": "Stock added successfully."}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], url_path='delete-product')
    def delete_product(self, request, pk=None):
        inventory = self.get_object()
        inventory.delete()
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
    def execute_transfer(self, request, pk=None):
        try:
            # Retrieve the Transfer object using the provided primary key
            transfer = self.get_object()

            # Check if the transfer status is 'pending' before executing
            if transfer.status != 'pending':
                return Response({"status": "Transfer is not pending, cannot execute."}, status=status.HTTP_400_BAD_REQUEST)

            # Deduct from the 'from' warehouse inventory (FIFO approach)
            from_inventory = Inventory.objects.filter(warehouse=transfer.source_warehouse, product=transfer.product).order_by('lot__purchase_date')

            quantity_left = transfer.quantity
            for inventory in from_inventory:
                if quantity_left <= 0:
                    break
                # Deduct from this lot
                if inventory.quantity <= quantity_left:
                    quantity_left -= inventory.quantity
                    inventory.deduct_quantity(inventory.quantity)
                else:
                    inventory.deduct_quantity(quantity_left)
                    quantity_left = 0

            # If there is still quantity left to be transferred, update the 'to' warehouse inventory
            to_inventory, created = Inventory.objects.get_or_create(warehouse=transfer.destination_warehouse, product=transfer.product, lot=inventory.lot)
            to_inventory.quantity += transfer.quantity
            to_inventory.save()

            # Update the transfer status to 'completed'
            transfer.status = 'completed'
            transfer.save()

            # Return success response
            return Response({"status": "Transfer executed successfully and marked as completed."})

        except Exception as e:
            # Handle any errors that may occur during the transfer process
            return Response({"status": str(e)}, status=status.HTTP_400_BAD_REQUEST)

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
            lot = Lot.objects.get(id=lot_id)
            store = Store.objects.get(id=request.user.store.id)  # Assuming store is linked to the user
        except Lot.DoesNotExist:
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

#General Warehouse Inventory Listing Viewset
class GeneralWarehouseInventoryViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['get'], url_path='general-warehouse-inventory')
    def list_general_inventory(self, request):
        inventory = Inventory.objects.filter(warehouse__warehouse_type='general')
        serializer = InventorySerializer(inventory, many=True)
        return Response(serializer.data)



