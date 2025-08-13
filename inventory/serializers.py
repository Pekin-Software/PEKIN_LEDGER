from rest_framework import serializers
from .models import Warehouse, Section, Inventory, Transfer, StockRequest
from products.models import Product, ProductVariant, ProductLot
from django.db import transaction
from products.serializers import ProductLotSerializer, ProductVariantSerializer
from django.utils import timezone
from datetime import timedelta

class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = ['tenant', 'warehouse_id', 'name', 'location', 'warehouse_type', 'store']

class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = ['warehouse', 'name', 'description', 'aisle_number', 'shelf_number']

class ProductNestedSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(read_only=True)
    product_image_url = serializers.SerializerMethodField()
    class Meta:
        model = Inventory.product.field.related_model
        fields = [
            'id', 'product_name', 'unit', 'threshold_value', 'product_image_url',
            'category', 'currency'
        ]

    def get_product_image_url(self, obj):
        request = self.context.get('request')
        if obj.product_image:
            return request.build_absolute_uri(obj.product_image.url)
        return None

class InventorySerializer(serializers.ModelSerializer):
    variant = ProductVariantSerializer(source='product_variant')
    product  = ProductNestedSerializer()
    stock_status = serializers.SerializerMethodField()
    total_quantity = serializers.SerializerMethodField()
    warehouse_type = serializers.CharField(source='warehouse.warehouse_type', read_only=True)
    overview = serializers.SerializerMethodField()
    variant_stock_status = serializers.SerializerMethodField()
    
    
    def get_variant_stock_status(self, obj):
        variant = obj.product_variant
        today = timezone.now().date()

        # Assuming 'lots' is the related name on ProductVariant.lots (adjust if different)
        lots = variant.lots.all()

        # Check if any lot is expired or expiring soon
        for lot in lots:
            if lot.expired_date and lot.expired_date < today:
                return "Expired"
        
        threshold = obj.product.threshold_value
        qty = obj.quantity

        if qty <= 0:
            return "Out of Stock"
        elif qty <= threshold:
            return "Low Stock"
        else:
            return "In Stock"

    @staticmethod
    def get_variants_warnings(inventories):
        today = timezone.now().date()
        low_stock_flag = False
        out_of_stock_flag = False
        expired_flag = False

        for inv in inventories:
            variant = inv.product_variant
            lots = variant.lots.all()

            # Check expired lots
            if any(lot.expired_date and lot.expired_date < today for lot in lots):
                expired_flag = True

            qty = inv.quantity
            threshold = inv.product.threshold_value

            if qty <= 0:
                out_of_stock_flag = True
            elif qty <= threshold:
                low_stock_flag = True

        warnings = []
        if expired_flag:
            warnings.append("Some variants have expired")
        if out_of_stock_flag:
            warnings.append("Some variants are out of stock")
        if low_stock_flag:
            warnings.append("Some variants are running low")

        return warnings


    class Meta:
        model = Inventory
        fields = [
            'id', 'product',
            'quantity', 'total_quantity','stock_status', 
            'warehouse_type', 'variant', 'overview', 'added_at', 'updated_at', 
            'variant_stock_status'
        ]

    def get_total_quantity(self, obj):
        return obj.compute_total_quantity()

    def get_stock_status(self, obj):
        return obj.compute_stock_status()
    
    # def get_overview(self, obj):
    #     if self.context.get('include_overview', False) and self.context.get('first_item_id') == obj.id:
    #         inventories = self.context.get('all_inventories', [])
    #         today = timezone.now().date()

    #         def calculate_stats(inventories_subset):
    #             product_ids = set()
    #             category_ids = set()
    #             in_stock = 0
    #             out_of_stock = 0
    #             low_stock = 0
    #             expiring_soon = 0

    #             for inv in inventories_subset:
    #                 product = inv.product
    #                 product_ids.add(product.id)
    #                 if product.category_id:
    #                     category_ids.add(product.category_id)

    #                 status = inv.compute_stock_status()

    #                 if status == "In Stock":
    #                     in_stock += 1
    #                 elif status == "Low Stock":
    #                     low_stock += 1
    #                 elif status == "Out of Stock":
    #                     out_of_stock += 1

    #                 if inv.product_variant:
    #                     for lot in inv.product_variant.lots.all():
    #                         if lot.expired_date and today < lot.expired_date <= today + timedelta(days=30):
    #                             expiring_soon += 1
    #                             break  # Count each inventory once even if multiple lots are expiring


    #             return {
    #                 "total_products": len(product_ids),
    #                 "total_categories": len(category_ids),
    #                 "in_stock": in_stock,
    #                 "out_of_stock": out_of_stock,
    #                 "low_stock": low_stock,
    #                 "expiring_soon": expiring_soon,
    #             }

    #         general_inventories = [inv for inv in inventories if inv.warehouse.warehouse_type == "general"]
    #         store_inventories = [inv for inv in inventories if inv.warehouse.warehouse_type != "general"]

    #         return {
    #             "general_inventory": calculate_stats(general_inventories),
    #             "store_inventory": calculate_stats(store_inventories),
    #         }
    #     return None

    def get_overview(self, obj):
        if self.context.get('include_overview', False) and self.context.get('first_item_id') == obj.id:
            inventories = self.context.get('all_inventories', [])
            today = timezone.now().date()

            def calculate_stats(inventories_subset):
                product_ids = set()
                category_ids = set()
                in_stock = 0
                out_of_stock = 0
                low_stock = 0
                expiring_soon = 0

                processed_variants = set()  # Prevent double-counting

                for inv in inventories_subset:
                    if not inv.product_variant:
                        continue

                    variant_id = inv.product_variant.id
                    if variant_id in processed_variants:
                        continue  # Skip duplicates (same variant across multiple lots)
                    processed_variants.add(variant_id)

                    product = inv.product
                    product_ids.add(product.id)
                    if product.category_id:
                        category_ids.add(product.category_id)

                    # Stock status at VARIANT level
                    status = inv.compute_stock_status()
                    if status == "In Stock":
                        in_stock += 1
                    elif status == "Low Stock":
                        low_stock += 1
                    elif status == "Out of Stock":
                        out_of_stock += 1

                    # Expiring soon → only if at least one lot of this variant is expiring
                    for lot in inv.product_variant.lots.all():
                        if lot.expired_date and today < lot.expired_date <= today + timedelta(days=30):
                            expiring_soon += 1
                            break

                return {
                    "total_products": len(product_ids),
                    "total_categories": len(category_ids),
                    "in_stock": in_stock,
                    "out_of_stock": out_of_stock,
                    "low_stock": low_stock,
                    "expiring_soon": expiring_soon,
                }

            general_inventories = [inv for inv in inventories if inv.warehouse.warehouse_type == "general"]
            store_inventories = [inv for inv in inventories if inv.warehouse.warehouse_type != "general"]

            return {
                "general_inventory": calculate_stats(general_inventories),
                "store_inventory": calculate_stats(store_inventories),
            }
        return None


#helper serializer to ensure bulk addition of Products
# class AddInventoryListSerializer(serializers.ListSerializer):
#     def create(self, validated_data_list):
#         if not validated_data_list:
#             return []

#         store = validated_data_list[0]['store']
#         tenant = store.tenant
#         warehouse = validated_data_list[0]['warehouse']

#         # Prepare keys to match existing inventories
#         key = (data['lot'].id, data['warehouse'].id, data['section'].id)

#         # Fetch existing inventories in bulk
#         existing_inventories = Inventory.objects.filter(
#             tenant=tenant,
#             warehouse=warehouse,
#             product_id__in=[k[0] for k in key],
#             product_variant_id__in=[k[1] for k in key],  # <-- FIX: include variant
#             lot_id__in=[k[2] for k in key],
#             section_id__in=[k[3] for k in key]  # <-- FIX: correct index for section
#         )

#         existing_map = {
#             (inv.lot_id, inv.warehouse_id, inv.section_id): inv
#             for inv in existing_inventories
#         }


#         new_inventories = []
#         inventories_to_update = []

#         for data in validated_data_list:
#             key = (data['product'].id, data['variant'].id, data['lot'].id, data['section'].id)
#             if key in existing_map:
#                 inv = existing_map[key]
#                 inv.quantity += data['quantity']
#                 inventories_to_update.append(inv)
#             else:
#                 new_inventories.append(Inventory(
#                     tenant=tenant,
#                     warehouse=warehouse,
#                     section=data['section'],
#                     product=data['product'],
#                     product_variant=data['variant'],
#                     lot=data['lot'],  # NEW: Assign lot
#                     quantity=data['quantity']
#                 ))

#         with transaction.atomic():
#             if new_inventories:
#                 Inventory.objects.bulk_create(new_inventories)
#             if inventories_to_update:
#                 Inventory.objects.bulk_update(inventories_to_update, ['quantity'])

#         return new_inventories + inventories_to_update
from django.db.models import Q

class AddInventoryListSerializer(serializers.ListSerializer):
    def create(self, validated_data_list):
        if not validated_data_list:
            return []

        store = validated_data_list[0]['store']
        tenant = store.tenant
        warehouse = validated_data_list[0]['warehouse']

        # Build all keys from the incoming data
        keys = [
            (
                data['product'].id,
                data['variant'].id,
                data['lot'].id,
                data['section'].id
            )
            for data in validated_data_list
        ]

        # Build a Q object to match exact combinations
        query = Q()
        for k in keys:
            query |= Q(
                product_id=k[0],
                product_variant_id=k[1],
                lot_id=k[2],
                section_id=k[3],
            )

        existing_inventories = Inventory.objects.filter(
            tenant=tenant,
            warehouse=warehouse
        ).filter(query)

        # Map by composite key
        existing_map = {
            (inv.product_id, inv.product_variant_id, inv.lot_id, inv.section_id): inv
            for inv in existing_inventories
        }

        new_inventories = []
        inventories_to_update = []

        # Check each incoming data
        for data in validated_data_list:
            key = (data['product'].id, data['variant'].id, data['lot'].id, data['section'].id)
            if key in existing_map:
                inv = existing_map[key]
                inv.quantity += data['quantity']
                inventories_to_update.append(inv)
            else:
                new_inventories.append(Inventory(
                    tenant=tenant,
                    warehouse=warehouse,
                    section=data['section'],
                    product=data['product'],
                    product_variant=data['variant'],
                    lot=data['lot'],
                    quantity=data['quantity']
                ))

        # Save in bulk
        with transaction.atomic():
            if new_inventories:
                Inventory.objects.bulk_create(new_inventories)
            if inventories_to_update:
                Inventory.objects.bulk_update(inventories_to_update, ['quantity'])

        return new_inventories + inventories_to_update

#Main Inventory serializer to add product the use the helper
class AddInventorySerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    variant_id = serializers.IntegerField() 
    lot_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    section_id = serializers.IntegerField(required=False)

    class Meta:
        list_serializer_class = AddInventoryListSerializer

    def validate(self, data):
        store = self.context.get('store')
        warehouse = self.context.get('warehouse')
        if not store or not warehouse:
            raise serializers.ValidationError("Internal server error: store or warehouse context missing.")

        data['store'] = store
        data['warehouse'] = warehouse

        # Validate Product
        try:
            product = Product.objects.get(id=data['product_id'], tenant=store.tenant)
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found for this tenant.")
        data['product'] = product

        try:
            variant = product.variants.get(id=data['variant_id'])
        except ProductVariant.DoesNotExist:
            raise serializers.ValidationError("Variant does not belong to the product.")
        data['variant'] = variant

         # Validate Lot
        try:
            lot = variant.lots.get(id=data['lot_id'])
        except ProductLot.DoesNotExist:
            raise serializers.ValidationError("Lot does not belong to this variant.")
        data['lot'] = lot

        # Validate or assign Section
        section_id = data.get('section_id')
        if section_id:
            try:
                section = warehouse.sections.get(id=section_id)
            except Section.DoesNotExist:
                raise serializers.ValidationError("Section not found in warehouse.")
        else:
            section = warehouse.sections.first()
            if not section:
                section = Section.objects.create(
                    warehouse=warehouse,
                    name=f"{warehouse.name} - Default Section"
                )
        data['section'] = section

        return data

class TransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transfer
        fields = ['source_warehouse', 'destination_warehouse', 'product', 'quantity', 'transfer_date', 'status', 'confirmed_by']

class StockRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockRequest
        fields = ['store', 'warehouse_from', 'warehouse_to', 'product', 'quantity_requested', 'status', 'request_date']
