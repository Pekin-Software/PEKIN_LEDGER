from rest_framework import serializers
from .models import Product, ProductAttribute, Category, Lot, Discount

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class DiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Discount
        fields = ['value']
    
    def generate_discount_name(lot):
    # Query the Discount model to find the maximum discount number associated with this lot
        existing_discounts = Discount.objects.filter(lot=lot)
        max_discount_number = 0

        # Extract the numbers from the discount names (e.g., "Discount 1", "Discount 2", etc.)
        for discount in existing_discounts:
            try:
                discount_number = int(discount.name.split(" ")[-1])  # Extract the number from "Discount X"
                max_discount_number = max(max_discount_number, discount_number)
            except ValueError:
                continue  # If there is no valid number, ignore this discount name

        # Generate the next discount name
        return f"Discount {max_discount_number + 1}"
    
    def create(self, validated_data):
        lot = self.context.get('lot')  # Get lot from context
        
        if lot is None:
            raise serializers.ValidationError("Lot is required to generate the discount name.")
        
          # Automatically generate the discount name
        discount_name = self.generate_discount_name(lot)
        validated_data['name'] = discount_name
        
        return Discount.objects.create(lot=lot, **validated_data)


class LotSerializer(serializers.ModelSerializer):
    wholesale_discount_price = DiscountSerializer(many=True, required=False)
    retail_discount_price = DiscountSerializer(many=True, required=False)

    class Meta:
        model = Lot
        fields = ['quantity', 'purchase_date', 'expired_date', 'wholesale_purchase_price', 
                  'retail_purchase_price', 'wholesale_selling_price', 'retail_selling_price',
                  'wholesale_discount_price','retail_discount_price']
    
    def create(self, validated_data):
        # Extract discount data separately
        wholesale_discounts_data = validated_data.pop("wholesale_discount_price", [])
        retail_discounts_data = validated_data.pop("retail_discount_price", [])
        product = self.context.get('product')  # Get the product from context
        
        #Create the Lot first
        lot = Lot.objects.create(product=product, **validated_data)

         #Create wholesale discounts and assign them
        wholesale_discounts = [
            Discount.objects.create(lot=lot, **discount_data) for discount_data in wholesale_discounts_data
        ]
        lot.wholesale_discount_price.set(wholesale_discounts) #Assign Many-to-Many discounts
        
        # Create retail discounts and assign them
        retail_discounts = [
            Discount.objects.create(lot=lot, **discount_data) for discount_data in retail_discounts_data
        ]
        lot.retail_discount_price.set(retail_discounts)  #Assign Many-to-Many discounts

            
        return Lot

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
        tenant = self.context['request'].tenant  # Assuming the tenant is available in request context
        product = Product.objects.create(tenant=tenant, **validated_data)

        for attribute_data in attributes_data:
            ProductAttribute.objects.create(product=product, **attribute_data)

            

        for lot_data in lots_data:
            wholesale_discounts = lot_data.pop('wholesale_discount_price', [])
            retail_discounts = lot_data.pop('retail_discount_price', [])
            lot = Lot.objects.create(product=product, **lot_data)
           # Create and associate wholesale discounts
            wholesale_discounts_created = [
                Discount.objects.create(lot=lot, **discount_data) for discount_data in wholesale_discounts
            ]
            lot.wholesale_discount_price.set(wholesale_discounts_created)

            # Create and associate retail discounts
            retail_discounts_created = [
                Discount.objects.create(lot=lot, **discount_data) for discount_data in retail_discounts
            ]
            lot.retail_discount_price.set(retail_discounts_created)
        return product


