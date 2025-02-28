from .views import index
from django.urls import path
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClientViewSet, DomainViewSet, UserViewSet, LoginViewSet

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'clients', ClientViewSet)
router.register(r'domains', DomainViewSet)
router.register(r'create', UserViewSet)
router.register(r'auth', LoginViewSet, basename='auth')

# The API URLs are now determined automatically by the router.
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', index),
    path('api/', include(router.urls)),
]
