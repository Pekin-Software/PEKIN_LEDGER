from django.urls import path, include
from rest_framework.routers import DefaultRouter

from accounting.views import FinancialReportViewSet

router = DefaultRouter()

router.register(
    r"financial-reports",
    FinancialReportViewSet,
    basename="financial-reports"
)

urlpatterns = [
    path("api/", include(router.urls)),
]

# GET /api/financial-reports/trial-balance/?store_id=1  - store
# GET /api/financial-reports/trial-balance/?store_id=1&start_date=2026-01-01&end_date=2026-01-31

# GET /api/financial-reports/master-trial-balance/ - Main
# GET /api/financial-reports/master-trial-balance/?start_date=2026-01-01&end_date=2026-01-31

# GET /api/financial-reports/store-p-and-l/?store_id=1 
# GET /api/financial-reports/store-p-and-l/?store_id=1&start_date=2026-01-01&end_date=2026-01-31

# GET /api/financial-reports/master-p-and-l/
# GET /api/financial-reports/master-p-and-l/?start_date=2026-01-01&end_date=2026-01-31

# GET /financial-reports/store-balance-sheet/
# GET /financial-reports/store-balance-sheet/?store_id=1&start_date=2026-01-01&end_date=2026-12-31

# GET /financial-reports/master-balance-sheet/
# GET /financial-reports/master-balance-sheet/?start_date=2026-01-01&end_date=2026-12-31

# GET /api/financial-reports/store-cash-flow/
# GET /api/financial-reports/store-cash-flow/?store_id=1&start_date=2026-01-01&end_date=2026-01-31

# GET /api/financial-reports/master-cash-flow/
# GET /api/financial-reports/master-cash-flow/?start_date=2026-01-01&end_date=2026-01-31

# GET /api/financial-reports/store-general-ledger/
# GET /api/financial-reports/store-general-ledger/?store_id=1&start_date=2026-01-01&end_date=2026-01-31

# GET /api/financial-reports/master-general-ledger/
# GET /api/financial-reports/master-general-ledger/?start_date=2026-01-01&end_date=2026-01-31