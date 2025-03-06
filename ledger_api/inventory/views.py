# from django.shortcuts import render

# # Create your views here.
# class CategoryViewSet(viewsets.ModelViewSet):
#     queryset = Category.objects.all()
#     serializer_class = CategorySerializer

# class ProductViewSet(viewsets.ModelViewSet):
#     queryset = Product.objects.all()
#     serializer_class = ProductSerializer

#     @action(detail=True, methods=['get'])
#     def flattened(self, request, pk=None):
#         product = self.get_object()
#         serializer = ProductSerializer(product)
        
#         # Get the attributes in a flattened format
#         attributes = serializer.data['attributes']
#         flattened_data = {
#             'SKU': product.sku,
#             'Product Name': product.name,
#             **attributes  # Add the dynamic attributes to the flattened structure
#         }

#         return Response(flattened_data)