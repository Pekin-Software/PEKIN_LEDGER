from rest_framework import serializers
from .models import Warehouse, Section, Inventory, Transfer, StockRequest

class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = ['tenant', 'warehouse_id', 'name', 'location', 'warehouse_type', 'store']

class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = ['warehouse', 'name', 'description', 'aisle_number', 'shelf_number']

class InventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventory
        fields = ['store', 'tenant', 'warehouse', 'section', 'product', 'lot', 'quantity']

class TransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transfer
        fields = ['source_warehouse', 'destination_warehouse', 'product', 'quantity', 'transfer_date', 'status', 'confirmed_by']

class StockRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockRequest
        fields = ['store', 'warehouse_from', 'warehouse_to', 'product', 'quantity_requested', 'status', 'request_date']
