from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ReconciliationViewSet

router = DefaultRouter()

router.register(
    r"reconciliations",
    ReconciliationViewSet,
    basename="reconciliations"
)

urlpatterns = [
    path("api/", include(router.urls)),
]

# /api/reconciliations/store-cash-transactions/?store_id=1&start_date=2026-01-01&end_date=2026-01-31 (applies to both master and store )
# /api/reconciliations/master-cash-transactions/

# /api/reconciliations/store-cash-reconciliations/?store_id=1
# /api/reconciliations/master-cash-reconciliations/

# /api/reconciliations/store-mobile-transactions/?store_id=1
# /api/reconciliations/master-mobile-transactions/

# /api/reconciliations/store-mobile-reconciliations/?store_id=1
# /api/reconciliations/master-mobile-reconciliations/

# /api/reconciliations/store-supplier-vat-transactions/?store_id=1
# /api/reconciliations/master-supplier-vat-transactions/

# /api/reconciliations/store-supplier-vat-reconciliations/?store_id=1
# /api/reconciliations/master-supplier-vat-reconciliations/

# /api/reconciliations/store-exceptions/?store_id=1
# /api/reconciliations/master-exceptions/

# /api/reconciliations/store-dashboard/?store_id=1
# /api/reconciliations/master-dashboard/