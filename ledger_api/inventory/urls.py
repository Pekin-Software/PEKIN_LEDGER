from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WarehouseViewSet, SectionViewSet, InventoryViewSet, TransferViewSet, StockRequestViewSet, GeneralWarehouseInventoryViewSet

router = DefaultRouter()
router.register(r'warehouses', WarehouseViewSet)
router.register(r'sections', SectionViewSet)
router.register(r'inventories', InventoryViewSet)
router.register(r'transfers', TransferViewSet)
router.register(r'stockrequests', StockRequestViewSet)
router.register(r'general-warehouse-inventory', GeneralWarehouseInventoryViewSet)

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

# POST /api/inventories/add-product/ - Add product to inventory

# GET /api/inventories/list/ - List inventory items

# PUT /api/inventories/{id}/update-product/ - Update inventory product

# DELETE /api/inventories/{id}/delete-product/ - Delete inventory product

# Transfer URLs:

# POST /api/transfers/create/ - Create a transfer

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

# General Warehouse Inventory URLs:

# GET /api/general-warehouse-inventory/general-warehouse-inventory/ - List inventory in general warehouse

