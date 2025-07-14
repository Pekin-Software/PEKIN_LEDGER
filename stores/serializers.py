from rest_framework import serializers
from .models import Store, Employee
from customers.models import Client  # Assuming tenant model is Client
from django.db import connection
from inventory.models import Inventory, Warehouse, Section
from products.models import Product, Lot
from django.db import transaction
from products.serializers import LotSerializer, ProductAttributeSerializer
from django.utils import timezone
from datetime import timedelta

class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ["id", "store_name", "tenant", "address", "city", "country", "phone_number"]
        read_only_fields = ["tenant"]

    def create(self, validated_data):
        # Get current tenant from schema_name (assuming django-tenants or similar is used)
        schema_name = connection.schema_name
        try:
            tenant = Client.objects.get(schema_name=schema_name)
        except Client.DoesNotExist:
            raise serializers.ValidationError("Tenant not found for this request.")

        # Attach the tenant to the store before saving
        validated_data["tenant"] = tenant
        return super().create(validated_data)

class EmployeeSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    position = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = ['user', 'position']

    def get_position(self, obj):
        return obj.user.position

# class AddInventorySerializer(serializers.Serializer):
#     product_id = serializers.IntegerField()
#     lot_id = serializers.IntegerField()
#     quantity = serializers.IntegerField(min_value=1)
#     section_id = serializers.IntegerField(required=False)  # Optional, can assign default section if none

#     def validate(self, data):
#         store = self.context.get('store')
#         warehouse = self.context.get('warehouse')
#         if not store or not warehouse:
#             raise serializers.ValidationError("Internal server error: store or warehouse context missing.")

#         data['store'] = store
#         data['warehouse'] = warehouse

#         # Validate product belongs to tenant
#         try:
#             product = Product.objects.get(id=data['product_id'], tenant=store.tenant)
#         except Product.DoesNotExist:
#             raise serializers.ValidationError("Product not found for this tenant.")
#         data['product'] = product

#         # Validate lot belongs to product
#         try:
#             lot = Lot.objects.get(id=data['lot_id'], product=product)
#         except Lot.DoesNotExist:
#             raise serializers.ValidationError("Lot not found for this product.")
#         data['lot'] = lot

#         # Validate or assign section
#         section_id = data.get('section_id')
#         if section_id:
#             try:
#                 section = warehouse.sections.get(id=section_id)
#             except Section.DoesNotExist:
#                 raise serializers.ValidationError("Section not found in warehouse.")
#         else:
#             section = warehouse.sections.first()
#             if not section:
#                 section = Section.objects.create(
#                     warehouse=warehouse,
#                     name=f"{warehouse.name} - Default Section"
#                 )
#         data['section'] = section

#         return data

#     def create(self, validated_data):
#         with transaction.atomic():
#             inventory, created = Inventory.objects.get_or_create(
#                 tenant=validated_data['store'].tenant,
#                 warehouse=validated_data['warehouse'],
#                 section=validated_data['section'],
#                 product=validated_data['product'],
#                 lot=validated_data['lot'],
#                 defaults={'quantity': validated_data['quantity']}
#             )
#             if not created:
#                 inventory.quantity += validated_data['quantity']
#                 inventory.save()
#         return inventory

#helper serializer to ensure bulk addition of Products
class AddInventoryListSerializer(serializers.ListSerializer):
    def create(self, validated_data_list):
        if not validated_data_list:
            return []

        store = validated_data_list[0]['store']
        tenant = store.tenant
        warehouse = validated_data_list[0]['warehouse']

        # Prepare keys to match existing inventories
        keys = {(item['product'].id, item['lot'].id, item['section'].id) for item in validated_data_list}

        # Fetch existing inventories in bulk
        existing_inventories = Inventory.objects.filter(
            tenant=tenant,
            warehouse=warehouse,
            product_id__in=[k[0] for k in keys],
            lot_id__in=[k[1] for k in keys],
            section_id__in=[k[2] for k in keys]
        )

        existing_map = {
            (inv.product_id, inv.lot_id, inv.section_id): inv for inv in existing_inventories
        }

        new_inventories = []
        inventories_to_update = []

        for data in validated_data_list:
            key = (data['product'].id, data['lot'].id, data['section'].id)
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
                    lot=data['lot'],
                    quantity=data['quantity']
                ))

        with transaction.atomic():
            if new_inventories:
                Inventory.objects.bulk_create(new_inventories)
            if inventories_to_update:
                Inventory.objects.bulk_update(inventories_to_update, ['quantity'])

        return new_inventories + inventories_to_update

#Main Inventory serializer to add product the use the helper
class AddInventorySerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
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

        # Validate Lot
        try:
            lot = Lot.objects.get(id=data['lot_id'], product=product)
        except Lot.DoesNotExist:
            raise serializers.ValidationError("Lot not found for this product.")
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


class ProductNestedSerializer(serializers.ModelSerializer):
    attributes = ProductAttributeSerializer(many=True)
    lots = serializers.SerializerMethodField()
    category = serializers.PrimaryKeyRelatedField(read_only=True)
    
    class Meta:
        model = Inventory.product.field.related_model
        fields = [
            'id', 'product_name', 'unit', 'threshold_value', 'product_image',
            'category', 'attributes', 'lots'
        ]

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.product_image:
            return request.build_absolute_uri(obj.product_image.url)
        return None
    
    def get_lots(self, product):
        inventory_qs = self.context.get('inventory_qs')
        if not inventory_qs:
            return []

        product_inventories = inventory_qs.filter(product=product)

        # Order by newest SKU (or change to 'lot__purchase_date' if you prefer)
        newest_inventory = product_inventories.order_by('-lot__sku').first()

        if newest_inventory and newest_inventory.lot:
            return [LotSerializer(newest_inventory.lot).data]

        return []


class InventoryForStoreSerializer(serializers.ModelSerializer):
    stock_status = serializers.SerializerMethodField()
    product = ProductNestedSerializer(read_only=True)
    total_quantity = serializers.SerializerMethodField()
    warehouse_type = serializers.CharField(source='warehouse.warehouse_type', read_only=True)
    
    overview = serializers.SerializerMethodField()

    class Meta:
        model = Inventory
        fields = ['id', 'product', 'quantity', 'stock_status', 'added_at', 
                  'updated_at','total_quantity', 'warehouse_type', 'overview']

    def get_total_quantity(self, obj):
        qty_map = self.context.get('qty_map', {})
        return qty_map.get(obj.product_id, 0)

    def get_stock_status(self, obj):
        total_quantity = self.get_total_quantity(obj)
        threshold = obj.product.threshold_value

        if obj.warehouse.warehouse_type == 'general':
            if total_quantity <= 0:
                return "Out of Stock"
            elif total_quantity <= threshold:
                return "Low Stock"
            else:
                return "In Stock"
        else:
            if obj.lot and obj.lot.expired_date and obj.lot.expired_date < timezone.now().date():
                return "Expired"

            if obj.quantity <= 0:
                return "Out of Stock"
            elif obj.quantity <= threshold:
                return "Low Stock"
            else:
                return "In Stock"

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

                for inv in inventories_subset:
                    product = inv.product
                    product_ids.add(product.id)
                    if product.category_id:
                        category_ids.add(product.category_id)

                    status = self.get_stock_status(inv)

                    if status == "In Stock":
                        in_stock += 1
                    elif status == "Low Stock":
                        low_stock += 1
                    elif status == "Out of Stock":
                        out_of_stock += 1

                    if inv.lot and inv.lot.expired_date:
                        if today < inv.lot.expired_date <= today + timedelta(days=30):
                            expiring_soon += 1

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
