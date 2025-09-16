
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('', include("customers.urls")), 
    path('', include("records.urls")),
    # path('', include("warehouses.urls")),
    path('', include("stores.urls")),
    path('', include("inventory.urls")),
    path('', include("products.urls")),
    path('', include("sales.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
