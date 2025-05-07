from django.db import transaction
from rest_framework import viewsets, status, decorators
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Product, ProductAttribute, Category, Lot, Discount
from .serializers import (
    ProductSerializer, ProductAttributeSerializer,
    CategorySerializer, LotSerializer, DiscountSerializer
)
from rest_framework.permissions import IsAuthenticated


# ViewSet to handle everything in one request
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]  # Enforces authentication
    
    def get_serializer_context(self):
        # Add 'request' to the context so it can be used in the serializer
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        return Response(ProductSerializer(product).data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['delete'], url_path='delete')
    def delete_product(self, request, pk=None):
        product = self.get_object()
        product.delete()
        return Response({"message": "Product deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['get'], url_path='list')
    def list_products(self, request):
        products = self.get_queryset()
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['put', 'patch'], url_path='update')
    def update_product(self, request, pk=None):
        product = self.get_object()
        serializer = self.get_serializer(product, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'], url_path='restock')
    def restock_product(self, request, pk=None):
        product = self.get_object()
        lot_data = request.data.get('lot', None)
        
        if not lot_data:
            return Response({"error": "Lot data is required for restocking."}, status=status.HTTP_400_BAD_REQUEST)
        
        lot_serializer = LotSerializer(data=lot_data)
        if lot_serializer.is_valid():
            lot_serializer.save(product=product)
            return Response(lot_serializer.data, status=status.HTTP_201_CREATED)
        return Response(lot_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Custom action for image upload
    @action(detail=True, methods=['post'], url_path='upload-image')
    def upload_image(self, request, pk=None):
        product = self.get_object()
        product.product_image = request.FILES.get("product_image")
        product.save()
        return Response({"status": "image uploaded", "image_url": product.product_image.url}, status=status.HTTP_200_OK)

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]  # Enforces authentication
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = serializer.save()
        return Response(CategorySerializer(category).data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['delete'], url_path='delete')
    def delete_category(self, request, pk=None):
        category = self.get_object()
        category.delete()
        return Response({"message": "Category deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['get'], url_path='list')
    def list_categories(self, request):
        categories = self.get_queryset()
        serializer = self.get_serializer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['put', 'patch'], url_path='update')
    def update_category(self, request, pk=None):
        category = self.get_object()
        serializer = self.get_serializer(category, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

class LotViewSet(viewsets.ModelViewSet):
    queryset = Lot.objects.all().order_by('-created_at')
    serializer_class = LotSerializer
    permission_classes = [IsAuthenticated]  # Enforces authentication
    
    @action(detail=True, methods=['put', 'patch'], url_path='update')
    def update_lot(self, request, pk=None):
        lot = self.get_object()
        serializer = self.get_serializer(lot, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], url_path='list')
    def list_lots(self, request):
        lots = self.get_queryset()
        serializer = self.get_serializer(lots, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DiscountViewSet(viewsets.ModelViewSet):
    queryset = Discount.objects.all()
    serializer_class = DiscountSerializer
    permission_classes = [IsAuthenticated]  # Enforces authentication
    
    @action(detail=False, methods=['get'], url_path='list')
    def list_discounts(self, request):
        """List all discounts"""
        discounts = self.get_queryset()
        serializer = self.get_serializer(discounts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['put', 'patch'], url_path='update')
    def update_discount(self, request, pk=None):
        """Update a discount"""
        discount = self.get_object()
        serializer = self.get_serializer(discount, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['delete'], url_path='delete')
    def delete_discount(self, request, pk=None):
        """Delete a discount"""
        discount = self.get_object()
        discount.delete()
        return Response({"message": "Discount deleted successfully"}, status=status.HTTP_204_NO_CONTENT)