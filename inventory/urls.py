from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WarehouseViewSet, SectionViewSet, InventoryViewSet, TransferViewSet, StockRequestViewSet

router = DefaultRouter()
router.register(r'warehouses', WarehouseViewSet, basename='warehouse' )
router.register(r'sections', SectionViewSet, basename='sections')
router.register(r'inventory', InventoryViewSet, basename='inventory')
router.register(r'transfers', TransferViewSet, basename='transefer')
router.register(r'stockrequests', StockRequestViewSet, basename='stockrequests')

urlpatterns = [
    path('api/', include(router.urls)),
]

# URL Path Breakdown
# Warehouse URLs:

# POST /api/warehouses/create/ - Create warehouse

# GET /api/warehouses/list/ - List all warehouses

# PUT /api/warehouses/{id}/update/ - Update a warehouse

# DELETE /api/warehouses/{id}/delete/ - Delete a warehouse

# Section URLs:

# POST /api/sections/create/ - Create section

# GET /api/sections/list/ - List sections (filterable by warehouse)

# PUT /api/sections/{id}/update/ - Update section

# DELETE /api/sections/{id}/delete/ - Delete section

# Inventory URLs:
# POST	/inventory/{store_id}/add-inventory/
# GET	/inventory/{store_id}/inventory/	
# GET	/inventory/main-inventory/	
# GET /api/inventory/main-inventory/?exclude_store_id=store_id 

# Transfer URLs:

# Transfer is created when stock request is confirm

# GET /api/transfers/list/ - List transfers

# PUT /api/transfers/{id}/update/ - Update transfer

# DELETE /api/transfers/{id}/delete/ - Delete transfer

# POST /api/transfers/{id}/execute/ - Execute transfer (admin only)

# Stock Request URLs:

# POST /api/stockrequests/create/ - Create stock request

# GET /stock-requests/list/
# To filter by status, you would call:

# http
# Copy
# GET /stock-requests/list/?status=pending
# To filter by a specific product ID, you would call:

# http
# Copy
# GET /stock-requests/list/?product=1
# You can combine filters, like so:

# http
# Copy
# GET /stock-requests/list/?status=pending&product=1

# PUT /api/stockrequests/{id}/update/ - Update stock request

# DELETE /api/stockrequests/{id}/delete/ - Delete stock request

# POST /api/stockrequests/{id}/confirm/ - Confirm stock request (admin only)


