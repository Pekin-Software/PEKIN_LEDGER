from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ComplianceViewSet


router = DefaultRouter()
router.register(
    r"compliance",
    ComplianceViewSet,
    basename="compliance"
)

urlpatterns = [
    path("api/", include(router.urls)),
]

# Dashboard reads:

# GET /api/compliance/store-vat-summary/?store_id=1
# GET /api/compliance/store-audit-logs/?store_id=1
# GET /api/compliance/store-pos-events/?store_id=1
# GET /api/compliance/store-inventory-events/?store_id=1
# GET /api/compliance/store-vat-filings/?store_id=1
# GET /api/compliance/store-periodlocks/?store_id=1

# Date filtered dashboard reads:

# GET /api/compliance/store-audit-logs/?store_id=1&start_date=2026-01-01&end_date=2026-01-31
# GET /api/compliance/store-pos-events/?store_id=1&start_date=2026-01-01&end_date=2026-01-31
# GET /api/compliance/store-inventory-events/?store_id=1&start_date=2026-01-01&end_date=2026-01-31
# GET /api/compliance/store-vat-summary/?store_id=1&start_date=2026-01-01&end_date=2026-01-31

# Controlled actions:

# POST /api/compliance/lock-store-period/?store_id=1
# POST /api/compliance/lock-master-period/
# POST /api/compliance/regenerate-store-vat-summary/?store_id=1
# POST /api/compliance/regenerate-store-vat-filing/?store_id=1
# POST /api/compliance/regenerate-master-vat-filing/
# POST /api/compliance/approve-vat-filing/
# POST /api/compliance/submit-vat-filing/

# Example POST body for period lock:

# {
#   "reporting_period": "2026-01",
#   "lock_type": "VAT",
#   "reason": "January VAT period reviewed and closed."
# }

# Example POST body for regeneration:

# {
#   "reporting_period": "2026-01"
# }

# Example POST body for approval/submission:

# {
#   "filing_id": 1
# }