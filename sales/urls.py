from pickle import GET
from rest_framework.routers import DefaultRouter
from .views import SaleViewSet, ExchangeRateViewSet, RefundViewSet
from django.urls import path, include

router = DefaultRouter()
router.register(r'sales', SaleViewSet, basename='sales')
router.register(r'rates', ExchangeRateViewSet, basename='exchange-rate')
router.register('refunds', RefundViewSet, basename='refunds')
urlpatterns = [
    path('api/', include(router.urls)),
]
# POST /sales/sale/
# GET /sales/listsales/
# GET /sales/lot-sales-report/?type=store
# GET /sales/lot-sales-report/?type=general
# GET /sales/lot-sales-report/?type=store&start_date=2025-07-01&end_date=2025-07-15
# Query parameters:

# type = store or general (default: general)

# start_date = YYYY-MM-DD (optional)

# end_date = YYYY-MM-DD (optional
# GET /sales/download-sales-report/?type=general&range=7days
# or
# GET /sales/download-sales-report/?type=store&range=custom&start_date=2025-07-01&end_date=2025-07-15

# Query parameters:

# type = store or general (default: general)

# range = today | 7days | 30days | custom (default: 30days)

# If range=custom, must include:

# start_date = YYYY-MM-DD

# end_date = YYYY-MM-DD

# GET /sales/lot-sales-report/?start_date=2025-07-01&end_date=2025-07-25&currency=USD&cashier_id=1&payment_method=Cash

# | HTTP Method | URL                         | Action                 |
# | ----------- | --------------------------- | ---------------------- |
# | GET         | `/rates/`                   | list all rates         |
# | POST        | `/rates/add-rate/`          | custom add rate action |
# |POST         |/api/sales/{sale_id}/cancel/ | cancel Sale fully
# |POST         |/api/sales/{sale_id}/add-payment/ | Make Payment
