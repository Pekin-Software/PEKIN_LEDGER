from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.db import transaction
from rest_framework.decorators import action
from .models import Product, Category, ProductLot, ProductVariant
from .serializers import (
    ProductSerializer,
    CategorySerializer, ProductLotSerializer
)

# # ViewSet to handle everything in one request
class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated] 
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
    @action(detail=False, methods=['post'], url_path='add-product')
    def add_product(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.save(tenant=self.request.user.domain)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['patch'], url_path='update-product')
    @transaction.atomic
    def update_product(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)  # partial=True here!
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        return Response(self.get_serializer(product).data)
    
    @transaction.atomic
    @action(detail=True, methods=['post'], url_path='restock-product')
    def restock(self, request, pk=None):
        product = self.get_object()
        tenant = request.tenant

        variant_id = request.data.get("variant_id")
        lots_data = request.data.get("lots", [])

        if not variant_id or not lots_data:
            return Response(
                {"detail": "variant_id and lots data are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Ensure variant belongs to this product
        try:
            variant = product.variants.get(id=variant_id)
        except ProductVariant.DoesNotExist:
            return Response(
                {"detail": "Variant not found for this product."},
                status=status.HTTP_404_NOT_FOUND
            )

        created_lots = []

        # Wrap the whole restock operation in a single atomic transaction
        with transaction.atomic():
            for lot_data in lots_data:
                serializer = ProductLotSerializer(data=lot_data)
                serializer.is_valid(raise_exception=True)
                lot = serializer.save(variant=variant)  # Inject variant before saving
                created_lots.append(ProductLotSerializer(lot).data)

        return Response(
            {"message": "Product restocked successfully.", "new_lots": created_lots},
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['delete'], url_path='delete')
    @transaction.atomic
    def delete_product(self, request, *args, **kwargs):
        product = self.get_object()

        # Optionally: check inventory quantities before deleting
        inventory_exists = Inventory.objects.filter(
            productvariant__product=product,
            quantity__gt=0
        ).exists()
        if inventory_exists:
            return Response(
                {"detail": "Cannot delete product with inventory quantities > 0."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # If no inventory or you want to delete anyway:
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    # Custom action for image upload
    @action(detail=True, methods=['post'], url_path='upload-image')
    @transaction.atomic
    def upload_image(self, request, pk=None):
        product = self.get_object()
        product.product_image = request.FILES.get("product_image")
        product.save()
        return Response({"status": "image uploaded", "image_url": product.product_image.url}, status=status.HTTP_200_OK)

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
