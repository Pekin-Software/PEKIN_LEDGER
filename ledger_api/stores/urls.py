# from rest_framework.routers import DefaultRouter
# from .views import StoreViewSet

# router = DefaultRouter()
# router.register(r'stores', StoreViewSet, basename='store')

# urlpatterns = router.urls


from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StoreEmployeeViewSet


router = DefaultRouter()
router.register(r'stores', StoreEmployeeViewSet, basename='store_employee')

urlpatterns = [
    path('api/', include(router.urls)),
]



