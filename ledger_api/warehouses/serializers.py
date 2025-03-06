# from rest_framework import serializers
# from .models import Warehouse, Section
# from inventory.serializers import ProductSerializer

# class SectionSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Section
#         fields = ['id', 'name', 'description', 'warehouse']

# class WarehouseSerializer(serializers.ModelSerializer):
#     sections = SectionSerializer(many=True, read_only=True)  # Show sections in warehouse details
#     products = ProductSerializer(many=True, read_only=True)  # Show products in warehouse details

#     class Meta:
#         model = Warehouse
#         fields = ['id', 'warehouse_id', 'tenant', 'name', 'location', 'sections', 'products']
#         read_only_fields = ['warehouse_id']
        

