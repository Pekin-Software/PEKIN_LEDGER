from django.db import transaction
from rest_framework import viewsets, status
from datetime import timedelta
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Product, Category, Lot
from .serializers import (
    ProductSerializer,
    CategorySerializer, LotSerializer
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.utils import timezone

# # ViewSet to handle everything in one request
class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]  # Enforces authentication
    queryset = Product.objects.all()
    
    def get_object(self):
        obj = super().get_object()
        if obj.tenant != self.request.tenant:
            raise PermissionDenied("Access denied.")
        return obj

    def get_queryset(self):
        return super().get_queryset().filter(tenant=self.request.tenant)
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['delete'], url_path='delete')
    @transaction.atomic
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
    @transaction.atomic
    def update_product(self, request, pk=None):
        product = self.get_object()
        serializer = self.get_serializer(product, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'], url_path='restock')
    @transaction.atomic
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
    @transaction.atomic
    def upload_image(self, request, pk=None):
        product = self.get_object()
        product.product_image = request.FILES.get("product_image")
        product.save()
        return Response({"status": "image uploaded", "image_url": product.product_image.url}, status=status.HTTP_200_OK)

    #DashBoard Summary 
    @action(detail=False, methods=['get'], url_path='overview')
    @transaction.atomic
    def overview(self, request):
        today = timezone.now().date()

        products = self.get_queryset().prefetch_related('lots') 
        categories = Category.objects.filter(products__in=products).distinct()

        total_products = products.count()
        total_categories = categories.count()

        in_stock = 0
        out_of_stock = 0
        low_stock = 0
        expiring_soon = 0

        for product in products:
            stock_status = product.stock_status
            if stock_status == "In Stock":
                in_stock += 1
            elif stock_status == "Out of Stock":
                out_of_stock += 1
            elif stock_status == "Low Stock":
                low_stock += 1

            if product.lots.filter(
                expired_date__gt=today,
                expired_date__lte=today + timedelta(days=30)
            ).exists():
                expiring_soon += 1

        return Response({
            "total_products": total_products,
            "total_categories": total_categories,
            "top_selling": 0,  # Placeholder
            "in_stock": in_stock,
            "out_of_stock": out_of_stock,
            "low_stock": low_stock,
            "expiring_soon": expiring_soon,
        }, status=status.HTTP_200_OK)

class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]  # Enforces authentication
    queryset = Product.objects.all()
    
    def get_object(self):
        obj = super().get_object()
        if obj.tenant != self.request.tenant:
            raise PermissionDenied("Access denied.")
        return obj
    def get_queryset(self):
        return Category.objects.all()
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = serializer.save()
        return Response(CategorySerializer(category).data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['delete'], url_path='delete')
    @transaction.atomic
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
    @transaction.atomic
    def update_category(self, request, pk=None):
        category = self.get_object()
        serializer = self.get_serializer(category, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

class LotViewSet(viewsets.ModelViewSet):
    serializer_class = LotSerializer
    permission_classes = [IsAuthenticated]  # Enforces authentication
    queryset = Product.objects.all()
    
    def get_object(self):
        obj = super().get_object()
        if obj.tenant != self.request.tenant:
            raise PermissionDenied("Access denied.")
        return obj
    
    def get_queryset(self):
        return Lot.objects.filter(product__tenant=self.request.tenant).order_by('-created_at')

    @action(detail=True, methods=['put', 'patch'], url_path='update')
    @transaction.atomic
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


