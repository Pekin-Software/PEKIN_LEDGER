from django.urls import path
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
<<<<<<< HEAD
from .views import  UserViewSet, LoginViewSet, CookieTokenRefreshView, healthz
from rest_framework_simplejwt.views import TokenRefreshView

# Create a router and register our viewsets with it.
=======
from .views import  UserViewSet, LoginViewSet, CookieTokenRefreshView, healthz, MyAPIView


>>>>>>> origin/main
router = DefaultRouter()
router.register(r'create', UserViewSet)
router.register(r'auth', LoginViewSet, basename='auth')

# The API URLs are now determined automatically by the router.
urlpatterns = [
    path('api/', include(router.urls)),
    path('api/token/refresh/', CookieTokenRefreshView.as_view(), name='token_refresh'), 
    path("healthz", healthz),
    path('api/protected/', MyAPIView.as_view(), name='protected-api'),
]   
