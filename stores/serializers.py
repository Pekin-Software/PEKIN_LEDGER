from rest_framework import serializers
from .models import Store, Employee
from customers.models import Client  # Assuming tenant model is Client
from django.db import connection
from inventory.models import Inventory, Warehouse, Section
from products.models import Product, Lot
from django.db import transaction
from products.serializers import LotSerializer, ProductAttributeSerializer
from django.utils import timezone


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

class AddInventorySerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    lot_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    section_id = serializers.IntegerField(required=False)  # Optional, can assign default section if none

    def validate(self, data):
        store = self.context.get('store')
        warehouse = self.context.get('warehouse')
        if not store or not warehouse:
            raise serializers.ValidationError("Internal server error: store or warehouse context missing.")

        data['store'] = store
        data['warehouse'] = warehouse

        # Validate product belongs to tenant
        try:
            product = Product.objects.get(id=data['product_id'], tenant=store.tenant)
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found for this tenant.")
        data['product'] = product

        # Validate lot belongs to product
        try:
            lot = Lot.objects.get(id=data['lot_id'], product=product)
        except Lot.DoesNotExist:
            raise serializers.ValidationError("Lot not found for this product.")
        data['lot'] = lot

        # Validate or assign section
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

    def create(self, validated_data):
        with transaction.atomic():
            inventory, created = Inventory.objects.get_or_create(
                tenant=validated_data['store'].tenant,
                warehouse=validated_data['warehouse'],
                section=validated_data['section'],
                product=validated_data['product'],
                lot=validated_data['lot'],
                defaults={'quantity': validated_data['quantity']}
            )
            if not created:
                inventory.quantity += validated_data['quantity']
                inventory.save()
        return inventory
        
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
    
    class Meta:
        model = Inventory
        fields = ['id', 'product', 'quantity', 'stock_status', 'added_at', 'updated_at','total_quantity', 'warehouse_type']

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

