from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .models import Warehouse, Section, Inventory, TransferLog, StockRequest, ProductLot, Product, Transfer
from stores.models import Employee, Store
from .serializers import (WarehouseSerializer, SectionSerializer, TransferSerializer, StockRequestSerializer, 
                AddInventorySerializer, InventorySerializer)
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

#Inventory Viewset (using Lot for FIFO)
class InventoryViewSet(viewsets.ViewSet):
    queryset = Inventory.objects.all()
    permission_classes = [IsAuthenticated, IsAdminUser]

    # @action(detail=True, methods=['post'], url_path='add-inventory', permission_classes=[IsAuthenticated])
    # def add_inventory(self, request, pk=None):
    #     try:
    #         store = Store.objects.get(pk=pk)
    #     except Store.DoesNotExist:
    #         return Response({"error": "Store not found."}, status=status.HTTP_404_NOT_FOUND)

    #     store_warehouse = store.warehouses.first()
    #     if not store_warehouse:
    #         return Response({"error": "Store has no warehouse."}, status=status.HTTP_400_BAD_REQUEST)

    #     serializer = AddInventorySerializer(
    #         data=request.data,
    #         many=True,
    #         context={'request': request, 'store': store, 'warehouse': store_warehouse}
    #     )
    #     serializer.is_valid(raise_exception=True)
    #     validated_data_list = serializer.validated_data

    #     general_warehouse = Warehouse.objects.filter(
    #         tenant=store.tenant, warehouse_type='general'
    #     ).first()
    #     if not general_warehouse:
    #         return Response({"error": "General warehouse not found."}, status=status.HTTP_400_BAD_REQUEST)

    #     # Get or create default section for the general warehouse
    #     general_section = Section.objects.filter(warehouse=general_warehouse).first()
    #     if not general_section:
    #         general_section = Section.objects.create(
    #             warehouse=general_warehouse,
    #             name=f"{general_warehouse.name} - Default Section"
    #         )

    #     results = []

    #     with transaction.atomic():
    #         # PRE-CHECK: Ensure stock is sufficient for all requested items
    #         for item in validated_data_list:
    #             product = item['product']
    #             variant = item['variant']
    #             if not variant:
    #                 return Response({
    #                     "error": f"Product {product.id} has no variants."
    #                 }, status=status.HTTP_400_BAD_REQUEST)

    #             quantity_needed = item['quantity']

    #             lots = ProductLot.objects.filter(
    #                 variant=variant,
    #                 quantity__gt=0
    #             ).order_by('purchase_date', 'id')

    #             total_available = sum(lot.quantity for lot in lots)
    #             if total_available < quantity_needed:
    #                 return Response({
    #                     "error": f"Insufficient stock for product {product.id} (variant {variant.id}). "
    #                             f"Requested {quantity_needed}, available {total_available}."
    #                 }, status=status.HTTP_400_BAD_REQUEST)

    #             general_inventory = Inventory.objects.filter(
    #                 warehouse=general_warehouse,
    #                 tenant=store.tenant,
    #                 section=general_section,
    #                 product=product,
    #                 product_variant=variant
    #             ).select_for_update().first()

    #             if not general_inventory or general_inventory.quantity < quantity_needed:
    #                 return Response({
    #                     "error": f"Insufficient general warehouse inventory for product {product.id}."
    #                 }, status=status.HTTP_400_BAD_REQUEST)

    #         # ALLOCATION: Deduct from general, lots, and add to store inventory
    #         for item in validated_data_list:
    #             product = item['product']
    #             variant = item['variant']
    #             quantity_needed = item['quantity']
    #             total_allocated = 0

    #             lots = ProductLot.objects.filter(
    #                 variant=variant,
    #                 quantity__gt=0
    #             ).order_by('purchase_date', 'id')

    #             general_inventory = Inventory.objects.get(
    #                 warehouse=general_warehouse,
    #                 tenant=store.tenant,
    #                 section=general_section,
    #                 product=product,
    #                 product_variant=variant
    #             )

    #             for lot in lots:
    #                 if quantity_needed <= 0:
    #                     break

    #                 available_qty = lot.quantity
    #                 allocate_qty = min(available_qty, quantity_needed)

    #                 # Deduct from lot
    #                 lot.quantity -= allocate_qty
    #                 lot.save()

    #                 # Deduct from general inventory
    #                 general_inventory.quantity -= allocate_qty
    #                 general_inventory.save()

    #                 # Always CREATE a new inventory row for the store
    #                 section = store_warehouse.sections.first()
    #                 if not section:
    #                     section = Section.objects.create(
    #                         warehouse=store_warehouse,
    #                         name=f"{store_warehouse.name} - Default Section"
    #                     )

    #                 # Get or create inventory for store, then update quantity
    #                 store_inventory, created = Inventory.objects.get_or_create(
    #                     warehouse=store_warehouse,
    #                     tenant=store.tenant,
    #                     section=section,
    #                     product=product,
    #                     lot=lot, 
    #                     product_variant=variant,
    #                     defaults={'quantity': 0}
    #                 )
    #                 store_inventory.quantity += allocate_qty
    #                 store_inventory.save()

    #                 TransferLog.objects.create(
    #                     source_inventory=general_inventory,
    #                     destination_inventory=store_inventory,
    #                     product=product,
    #                     product_variant=variant,
    #                     lot=lot,
    #                     quantity=allocate_qty,
    #                     direction='to_store',
    #                     tenant=store.tenant
    #                 )
    #                 total_allocated += allocate_qty
    #                 quantity_needed -= allocate_qty

    #                 results.append({
    #                     "product_id": product.id,
    #                     "variant_id": variant.id,
    #                     "lot.id": lot.id,
    #                     "quantity_allocated": total_allocated,
    #                 })

    #     return Response({
    #         "status": "success",
    #         "message": "Inventory allocation completed.",
    #         "results": results
    #     }, status=status.HTTP_200_OK)
    @action(detail=True, methods=['post'], url_path='add-inventory', permission_classes=[IsAuthenticated])
    def add_inventory(self, request, pk=None):
        try:
            store = Store.objects.get(pk=pk)
        except Store.DoesNotExist:
            return Response({"error": "Store not found."}, status=status.HTTP_404_NOT_FOUND)

        store_warehouse = store.warehouses.first()
        if not store_warehouse:
            return Response({"error": "Store has no warehouse."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = AddInventorySerializer(
            data=request.data,
            many=True,
            context={'request': request, 'store': store, 'warehouse': store_warehouse}
        )
        serializer.is_valid(raise_exception=True)
        validated_data_list = serializer.validated_data

        general_warehouse = Warehouse.objects.filter(
            tenant=store.tenant, warehouse_type='general'
        ).first()
        if not general_warehouse:
            return Response({"error": "General warehouse not found."}, status=status.HTTP_400_BAD_REQUEST)

        # Get or create default section for the general warehouse
        general_section = Section.objects.filter(warehouse=general_warehouse).first()
        if not general_section:
            general_section = Section.objects.create(
                warehouse=general_warehouse,
                name=f"{general_warehouse.name} - Default Section"
            )

        results = []

        with transaction.atomic():
            # PRE-CHECK: Ensure stock is sufficient for all requested items
            for item in validated_data_list:
                product = item['product']
                variant = item['variant']
                if not variant:
                    return Response({
                        "error": f"Product {product.id} has no variants."
                    }, status=status.HTTP_400_BAD_REQUEST)

                quantity_needed = item['quantity']

                lots = ProductLot.objects.filter(
                    variant=variant,
                    quantity__gt=0
                ).order_by('purchase_date', 'id')

                total_available = sum(lot.quantity for lot in lots)
                if total_available < quantity_needed:
                    return Response({
                        "error": f"Insufficient stock for product {product.id} (variant {variant.id}). "
                                f"Requested {quantity_needed}, available {total_available}."
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Check total quantity in general inventory across lots
                total_general_qty = Inventory.objects.filter(
                    warehouse=general_warehouse,
                    tenant=store.tenant,
                    section=general_section,
                    product=product,
                    product_variant=variant
                ).aggregate(total=models.Sum('quantity'))['total'] or 0

                if total_general_qty < quantity_needed:
                    return Response({
                        "error": f"Insufficient general warehouse inventory for product {product.id}."
                    }, status=status.HTTP_400_BAD_REQUEST)

            # ALLOCATION: Deduct from general, lots, and add to store inventory
            for item in validated_data_list:
                product = item['product']
                variant = item['variant']
                quantity_needed = item['quantity']
                total_allocated = 0

                lots = ProductLot.objects.filter(
                    variant=variant,
                    quantity__gt=0
                ).order_by('purchase_date', 'id')

                for lot in lots:
                    if quantity_needed <= 0:
                        break

                    allocate_qty = min(lot.quantity, quantity_needed)

                    # Fetch the corresponding general inventory for this lot
                    general_inventory = Inventory.objects.filter(
                        warehouse=general_warehouse,
                        tenant=store.tenant,
                        section=general_section,
                        product=product,
                        product_variant=variant,
                        lot=lot
                    ).select_for_update().first()

                    if not general_inventory or general_inventory.quantity < allocate_qty:
                        return Response({
                            "error": f"Insufficient general warehouse inventory for product {product.id} in lot {lot.id}."
                        }, status=status.HTTP_400_BAD_REQUEST)

                    # Deduct from lot and general inventory
                    lot.quantity -= allocate_qty
                    lot.save()

                    general_inventory.quantity -= allocate_qty
                    general_inventory.save()

                    # Always get or create (reuse) store inventory row for this lot
                    section = store_warehouse.sections.first()
                    if not section:
                        section = Section.objects.create(
                            warehouse=store_warehouse,
                            name=f"{store_warehouse.name} - Default Section"
                        )

                    store_inventory, created = Inventory.objects.get_or_create(
                        warehouse=store_warehouse,
                        tenant=store.tenant,
                        section=section,
                        product=product,
                        lot=lot,
                        product_variant=variant,
                        defaults={'quantity': 0}
                    )
                    store_inventory.quantity += allocate_qty
                    store_inventory.save()

                    # Create transfer log
                    TransferLog.objects.create(
                        source_inventory=general_inventory,
                        destination_inventory=store_inventory,
                        product=product,
                        product_variant=variant,
                        lot=lot,
                        quantity=allocate_qty,
                        direction='to_store',
                        tenant=store.tenant
                    )

                    total_allocated += allocate_qty
                    quantity_needed -= allocate_qty

                    results.append({
                        "product_id": product.id,
                        "variant_id": variant.id,
                        "lot_id": lot.id,
                        "quantity_allocated": total_allocated,
                    })

        return Response({
            "status": "success",
            "message": "Inventory allocation completed.",
            "results": results
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='inventory', permission_classes=[IsAuthenticated, IsStoreAssigned])
    def store_inventory(self, request, pk=None):
        try:
            store = Store.objects.get(pk=pk)
        except Store.DoesNotExist:
            return Response({"error": "Store not found in this tenant."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, store)
        client = store.tenant

        # Get all warehouses for the store
        store_warehouses = store.warehouses.all()
        if not store_warehouses.exists():
            return Response({"error": "No warehouse found for this store."}, status=status.HTTP_404_NOT_FOUND)

        # Filter inventory for store warehouses
        store_inventory_qs = Inventory.objects.filter(
            warehouse__in=store_warehouses
            ).select_related(
            'product', 'product_variant', 'product__category'
        )

        all_inventories = list(store_inventory_qs)

        serializer = InventorySerializer(
            store_inventory_qs,
            many=True,
            context={
                'request': request,
                'include_overview': True,
                'first_item_id': all_inventories[0].id if all_inventories else None,
                'all_inventories': all_inventories
            }
        )
        warnings = InventorySerializer.get_variants_warnings(all_inventories)
        serialized_data = serializer.data

        # Group by product.id
        grouped = defaultdict(list)
        for item in serialized_data:
            grouped[item['product']['id']].append(item)

        # Build the grouped response just like main_inventory does
        response_data = []
        for product_id, items in grouped.items():
            first = items[0]
            
            overview_data = first['overview'] if first['warehouse_type'] == 'store' else None
            if overview_data:
                overview_data = {"Store Inventory": overview_data.get("store_inventory")}

            # Aggregate total quantity across all variants/lots
            total_quantity = sum(int(i['total_quantity']) for i in items if i['total_quantity'])

            # Aggregate stock status at product level
            variant_statuses = [i['variant_stock_status'] for i in items]
            if any(status == "In Stock" for status in variant_statuses):
                product_stock_status = "In Stock"
            elif any(status == "Low Stock" for status in variant_statuses):
                product_stock_status = "Low Stock"
            else:
                product_stock_status = "Out of Stock"

            grouped_item = {
                "id": first['id'],
                "product": first['product'],
                "total_quantity": total_quantity,
                "stock_status": product_stock_status,
                "warehouse_type": first['warehouse_type'],
                "variants": [{
                    **i['variant'],
                    'stock_status': i['variant_stock_status']
                } for i in items],
                "overview": overview_data,
                "warnings": warnings,
                "added_at": first['added_at'],
                "updated_at": first['updated_at'],
            }
            response_data.append(grouped_item)


        return Response(response_data, status=status.HTTP_200_OK)
   
    @action(detail=False, methods=['get'], url_path='main-inventory', permission_classes=[IsAuthenticated])
    def main_inventory(self, request):
        client = request.user.domain

        warehouse = Warehouse.objects.filter(
            tenant=client,
            warehouse_type='general'
        ).first()
        if not warehouse:
            return Response({"error": "General warehouse not found."}, status=status.HTTP_404_NOT_FOUND)

        # Inventory for general warehouse
        main_inventory_qs = Inventory.objects.filter(
            warehouse=warehouse
        ).select_related('product', 'product_variant', 'product__category')

        # Exclude store items if provided
        exclude_store_id = request.query_params.get('exclude_store_id')
        if exclude_store_id:
            store_warehouses = Warehouse.objects.filter(
                store_id=exclude_store_id,
                tenant=client
            ).values_list('id', flat=True)
            store_inventory_pairs = Inventory.objects.filter(
                warehouse_id__in=store_warehouses
            ).values_list('product_id', 'product_variant_id')
            main_inventory_qs = main_inventory_qs.exclude(
                product_id__in=[p for p, _ in store_inventory_pairs],
                product_variant_id__in=[v for _, v in store_inventory_pairs]
            )

        # Fetch all products in this inventory
        product_ids = main_inventory_qs.values_list('product_id', flat=True).distinct()
        products = Product.objects.filter(id__in=product_ids).prefetch_related('variants__attributes', 'variants__lots')
        all_inventories = list(main_inventory_qs)
    
        serializer = InventorySerializer(
            main_inventory_qs,
            many=True,
            context={
                'request': request,
                'include_overview': True,  # Enable overview
                'first_item_id': all_inventories[0].id if all_inventories else None,  # First item ID
                'all_inventories': all_inventories  # Pass all for overview stats
            }
        )
        warnings = InventorySerializer.get_variants_warnings(all_inventories)

        serialized_data = serializer.data

        # Group by product.id
        grouped = defaultdict(list)
        for item in serialized_data:
            grouped[item['product']['id']].append(item)

        # Build the grouped response
        response_data = []
        for product_id, items in grouped.items():
            first = items[0]
            # Group variants by variant.id to prevent duplicates
            variant_map = {}
            for i in items:
                variant_id = i['variant']['id']
                if variant_id not in variant_map:
                    variant_map[variant_id] = {
                        **i['variant'],
                        'stock_status': i['variant_stock_status'],
                        'lots': i['variant']['lots']  # Start with initial lots
                    }
                else:
                    # Merge lots (avoid duplication by lot.id)
                    existing_lots = {lot['id'] for lot in variant_map[variant_id]['lots']}
                    new_lots = [lot for lot in i['variant']['lots'] if lot['id'] not in existing_lots]
                    variant_map[variant_id]['lots'].extend(new_lots)

            variants = list(variant_map.values())

            # Only include overview if warehouse_type is 'general', else None
            overview_data = first['overview'] if first['warehouse_type'] == 'general' else None
            if overview_data:
                # Remove store_inventory key, only keep general_inventory
                overview_data = {
                    "general_inventory": overview_data.get("general_inventory")
                }

            grouped_item = {
                "id": first['id'],
                "product": first['product'],
                "total_quantity": first['total_quantity'],  # already computed correctly
                "stock_status": first['stock_status'],
                "warehouse_type": first['warehouse_type'],
                "variants": variants,  # <-- Use the deduplicated variants
                "overview": overview_data,
                "warnings": warnings,
                "added_at": first['added_at'],
                "updated_at": first['updated_at'],
            }
            response_data.append(grouped_item)

        return Response(response_data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='return-inventory', permission_classes=[IsAuthenticated])
    def return_inventory(self, request, pk=None):
        try:
            store = Store.objects.get(pk=pk)
        except Store.DoesNotExist:
            return Response({"error": "Store not found."}, status=status.HTTP_404_NOT_FOUND)

        store_warehouse = store.warehouses.first()
        if not store_warehouse:
            return Response({"error": "Store has no warehouse."}, status=status.HTTP_400_BAD_REQUEST)

        items_to_return = request.data
        if not isinstance(items_to_return, list):
            return Response({"error": "Invalid input format, expected a list."}, status=status.HTTP_400_BAD_REQUEST)

        results = []
        with transaction.atomic():
            for item in items_to_return:
                product_id = item.get('product_id')
                variant_id = item.get('variant_id')
                lot_id = item.get('lot_id')
                quantity_to_return = item.get('quantity')

                if not product_id or not variant_id or not lot_id or not isinstance(quantity_to_return, int) or quantity_to_return <= 0:
                    return Response({"error": "Invalid product, variant, lot, or quantity."}, status=status.HTTP_400_BAD_REQUEST)

                # Get store inventories (lot-specific)
                store_inventories = Inventory.objects.filter(
                    warehouse=store_warehouse,
                    tenant=store.tenant,
                    product_id=product_id,
                    product_variant_id=variant_id,
                    lot_id=lot_id
                ).select_for_update().order_by('added_at')

                total_store_qty = store_inventories.aggregate(total=models.Sum('quantity'))['total'] or 0
                if total_store_qty < quantity_to_return:
                    return Response({
                        "error": f"Insufficient store inventory for product {product_id} variant {variant_id} lot {lot_id}. "
                                f"Requested: {quantity_to_return}, Available: {total_store_qty}"
                    }, status=status.HTTP_400_BAD_REQUEST)

                qty_left = quantity_to_return

                for store_inventory in store_inventories:
                    if qty_left <= 0:
                        break

                    # Find transfer logs for this store inventory (oldest first)
                    transfer_logs = TransferLog.objects.filter(
                        destination_inventory=store_inventory,
                        direction='to_store',
                        product_id=product_id,
                        product_variant_id=variant_id,
                        lot_id=lot_id
                    ).select_for_update().order_by('transferred_at')

                    for log in transfer_logs:
                        if qty_left <= 0:
                            break
                        restore_qty = min(log.quantity, qty_left)

                        # Deduct from store inventory
                        store_inventory.quantity -= restore_qty
                        store_inventory.save()

                        # Restore to the exact source inventory (general warehouse)
                        general_inventory = log.source_inventory
                        general_inventory.quantity += restore_qty
                        general_inventory.save()

                        # ALSO update the ProductLot quantity
                        product_lot = general_inventory.lot
                        product_lot.quantity += restore_qty
                        product_lot.save()

                        # Create reverse log
                        TransferLog.objects.create(
                            source_inventory=store_inventory,
                            destination_inventory=general_inventory,
                            product_id=product_id,
                            product_variant_id=variant_id,
                            lot_id=lot_id,
                            quantity=restore_qty,
                            direction='to_general',
                            tenant=store.tenant
                        )

                        # Reduce original log's quantity (if partial return)
                        log.quantity -= restore_qty
                        if log.quantity <= 0:
                            log.delete()
                        else:
                            log.save()

                        qty_left -= restore_qty

                    results.append({
                        "product_id": product_id,
                        "variant_id": variant_id,
                        "lot_id": lot_id,
                        "quantity_returned": quantity_to_return - qty_left
                    })

        return Response({
            "status": "success",
            "message": "Inventory returned to general warehouse successfully.",
            "results": results
        }, status=status.HTTP_200_OK)


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

