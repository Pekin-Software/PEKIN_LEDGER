from django.urls import path
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import  SubaccountViewSet

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'users', SubaccountViewSet, basename='subaccount')

# The API URLs are now determined automatically by the router.
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
]
