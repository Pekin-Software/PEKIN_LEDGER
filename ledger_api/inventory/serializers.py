# class CategorySerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Category
#         fields = '__all__'

# class ProductSerializer(serializers.ModelSerializer):
#     attributes = serializers.SerializerMethodField()

#     class Meta:
#         model = Product
#         fields = ['sku', 'name', 'category', 'price', 'quantity', 'attributes']
    
#     def get_attributes(self, obj):
#         # Fetch all the attributes for the product and return as a dictionary
#         attributes = {attr.name: attr.value for attr in obj.attributes.all()}
#         return attributes

