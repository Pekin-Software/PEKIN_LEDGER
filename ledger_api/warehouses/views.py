# from rest_framework import viewsets, permissions, filters
# from rest_framework.decorators import action
# from rest_framework.response import Response
# from django_filters.rest_framework import DjangoFilterBackend
# from .models import Warehouse, Section
# from .serializers import WarehouseSerializer, SectionSerializer
# from inventory.models import Product
# from inventory.serializers import ProductSerializer

# class IsAdminOrManager(permissions.BasePermission):
#     def has_permission(self, request, view):
#         return request.user.is_authenticated and (request.user.is_staff or request.user.role in ['admin', 'manager'])

# class WarehouseViewSet(viewsets.ModelViewSet):
#     queryset = Warehouse.objects.all()
#     serializer_class = WarehouseSerializer
#     filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
#     filterset_fields = ['sections__name', 'products__category', 'products__expiration_date', 'products__created_at', 'products__updated_at', 'products__price']
#     ordering_fields = ['name', 'location']
#     permission_classes = [permissions.IsAdminUser]  # Only admins can manage warehouses

#     @action(detail=False, methods=['post'], permission_classes=[permissions.IsAdminUser], url_path='create')
#     def create_warehouse(self, request):
#         """ Create a new warehouse """
#         serializer = self.get_serializer(data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data, status=201)
#         return Response(serializer.errors, status=400)

#     @action(detail=True, methods=['put', 'patch'], permission_classes=[permissions.IsAdminUser], url_path='update')
#     def update_warehouse(self, request, pk=None):
#         """ Update an existing warehouse """
#         warehouse = self.get_object()
#         serializer = self.get_serializer(warehouse, data=request.data, partial=True)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data)
#         return Response(serializer.errors, status=400)

#     @action(detail=True, methods=['delete'], permission_classes=[permissions.IsAdminUser], url_path='delete')
#     def delete_warehouse(self, request, pk=None):
#         """ Delete a warehouse """
#         warehouse = self.get_object()
#         warehouse.delete()
#         return Response(status=204)

#     @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated], url_path='list-warehouse')
#     def list_warehouse(self, request):
#         """ List all warehouses """
#         warehouses = self.get_queryset()
#         serializer = self.get_serializer(warehouses, many=True)
#         return Response(serializer.data)

#     @action(detail=True, methods=['get'], permission_classes=[IsAdminOrManager], url_path='product-list')
#     def product_list(self, request, pk=None):
#         """ List all products in a specific warehouse with filtering options """
#         warehouse = self.get_object()
#         products = Product.objects.filter(section__warehouse=warehouse)
#         section = request.query_params.get('section')
#         category = request.query_params.get('category')
#         expiration_date = request.query_params.get('expiration_date')
#         created_at = request.query_params.get('created_at')
#         updated_at = request.query_params.get('updated_at')
#         price = request.query_params.get('price')

#         if section:
#             products = products.filter(section__name=section)
#         if category:
#             products = products.filter(category=category)
#         if expiration_date:
#             products = products.filter(expiration_date=expiration_date)
#         if created_at:
#             products = products.filter(created_at=created_at)
#         if updated_at:
#             products = products.filter(updated_at=updated_at)
#         if price:
#             products = products.filter(price=price)

#         serializer = ProductSerializer(products, many=True)
#         return Response(serializer.data)

# class SectionViewSet(viewsets.ModelViewSet):
#     queryset = Section.objects.all()
#     serializer_class = SectionSerializer
#     permission_classes = [permissions.IsAdminUser]  # Only admins can manage sections

#     @action(detail=False, methods=['post'], permission_classes=[permissions.IsAdminUser], url_path='create')
#     def create_section(self, request):
#         """ Create a new section """
#         serializer = self.get_serializer(data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data, status=201)
#         return Response(serializer.errors, status=400)

#     @action(detail=True, methods=['put', 'patch'], permission_classes=[permissions.IsAdminUser], url_path='update')
#     def update_section(self, request, pk=None):
#         """ Update an existing section """
#         section = self.get_object()
#         serializer = self.get_serializer(section, data=request.data, partial=True)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data)
#         return Response(serializer.errors, status=400)

#     @action(detail=True, methods=['delete'], permission_classes=[permissions.IsAdminUser], url_path='delete')
#     def delete_section(self, request, pk=None):
#         """ Delete a section """
#         section = self.get_object()
#         section.delete()
#         return Response(status=204)
