from rest_framework import serializers
from .models import Product, ProductAttribute, Category, Lot
from rest_framework.exceptions import ValidationError
from  inventory.models import Warehouse, Inventory

class CategorySerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    class Meta:
        model = Category
        fields = ['id','name']

class LotSerializer(serializers.ModelSerializer):

    class Meta:
        model = Lot
        fields = ['id','sku', 'quantity', 'purchase_date', 'wholesale_quantity', 'purchase_price', 
                  'wholesale_selling_price', 'retail_selling_price', 
                  'expired_date',
                  ]
    
    def update(self, instance, validated_data):
        new_quantity = validated_data.get('quantity', instance.quantity)
        old_quantity = instance.quantity
        quantity_diff = new_quantity - old_quantity

        if quantity_diff != 0:
            product = instance.product
            tenant = product.tenant

            warehouse = Warehouse.objects.filter(tenant=tenant, warehouse_type='general').first()
            if not warehouse:
                raise ValidationError("No general warehouse found for this tenant.")

            section = warehouse.sections.first()
            if not section:
                raise ValidationError("No section found for warehouse.")

            try:
                inventory = Inventory.objects.get(
                    product=product,
                    lot=instance,
                    warehouse=warehouse,
                    section=section
                )
            except Inventory.DoesNotExist:
                raise ValidationError("Inventory does not exist for this lot.")

            new_inventory_quantity = inventory.quantity + quantity_diff
            if new_inventory_quantity < 0:
                raise ValidationError(
                    {"quantity": f"Cannot reduce quantity. It would cause inventory to go negative ({new_inventory_quantity})."}
                )

        # Proceed with update
        return super().update(instance, validated_data)


class ProductAttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductAttribute
        fields = ['name', 'value']
    
    
    def create(self, validated_data):
        product = self.context.get('product')  # Get the product from context
        return ProductAttribute.objects.create(product=product, **validated_data)

class ProductSerializer(serializers.ModelSerializer):
    attributes = ProductAttributeSerializer(many=True)
    lots = LotSerializer(many=True)
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    image_url = serializers.SerializerMethodField()

    def get_lots(self, obj):
        # Return lots ordered by expired_date descending (newest first)
        sorted_lots = obj.lots.order_by('-expired_date')
        return LotSerializer(sorted_lots, many=True).data

    class Meta:
        model = Product
        exclude = ['tenant']    

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.product_image:
            return request.build_absolute_uri(obj.product_image.url)
        return None

    def create(self, validated_data):
        attributes_data = validated_data.pop('attributes', [])
        lots_data = validated_data.pop('lots', [])
        tenant = self.context['request'].tenant  
        product = Product.objects.create(tenant=tenant, **validated_data)
        

        for attribute_data in attributes_data:
            ProductAttribute.objects.create(product=product, **attribute_data)

        for lot_data in lots_data:
            Lot.objects.create(product=product, **lot_data)
          
        return product