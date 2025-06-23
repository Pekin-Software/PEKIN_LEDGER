from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, CategoryViewSet, LotViewSet

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'lots', LotViewSet, basename='lot')

urlpatterns = [
    path('api/', include(router.urls)),
]

# GET	/products/	List all products
# POST	/products/	Create a new product
# PUT/PATCH	/products/{id}/	Update a product
# DELETE	/products/{id}/	Delete a product
# POST	/products/{id}/restock/	Add a new lot (restocking)
# GET	/categories/	List all categories
# POST	/categories/	Create a new category
# PUT/PATCH	/categories/{id}/	Update a category
# DELETE	/categories/{id}/	Delete a category
# GET	/lots/	List all lots (newest first)
# PUT/PATCH	/lots/{id}/update/	Update a lot