from rest_framework import serializers
from .models import Product, ProductAttribute, Category, Lot, Discount

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class DiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Discount
        fields = '__all__'

class LotSerializer(serializers.ModelSerializer):
    wholesale_discount_price = DiscountSerializer(many=True)
    retail_discount_price = DiscountSerializer(many=True)

    class Meta:
        model = Lot
        fields = '__all__'

class ProductAttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductAttribute
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    attributes = ProductAttributeSerializer(many=True)
    lots = LotSerializer(many=True)
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())

    class Meta:
        model = Product
        fields = '__all__'

    def create(self, validated_data):
        attributes_data = validated_data.pop('attributes', [])
        lots_data = validated_data.pop('lots', [])
        product = Product.objects.create(**validated_data)

        for attribute_data in attributes_data:
            ProductAttribute.objects.create(product=product, **attribute_data)

        for lot_data in lots_data:
            wholesale_discounts = lot_data.pop('wholesale_discount_price', [])
            retail_discounts = lot_data.pop('retail_discount_price', [])
            lot = Lot.objects.create(product=product, **lot_data)
            lot.wholesale_discount_price.set(wholesale_discounts)
            lot.retail_discount_price.set(retail_discounts)

        return product
