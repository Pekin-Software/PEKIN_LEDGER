from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TenantViewSet

# Initialize the router
router = DefaultRouter()
router.register(r'', TenantViewSet, basename='Create_Store')

urlpatterns = [
    path('api/', include(router.urls)),  # Includes the ViewSet routes
]
