from django.urls import path, include
from rest_framework.routers import DefaultRouter

from taxation.views import (
    TaxClassViewSet,
    TaxPeriodViewSet,
    VATLedgerViewSet,
    StoreVATSummaryViewSet,
    VATReturnViewSet,
    VATAdjustmentViewSet,
    TaxPaymentViewSet,
)

router = DefaultRouter()

router.register("tax-classes", TaxClassViewSet, basename="tax-classes")
router.register("tax-periods", TaxPeriodViewSet, basename="tax-periods")
router.register("vat-ledger", VATLedgerViewSet, basename="vat-ledger")
router.register("store-vat-summaries", StoreVATSummaryViewSet, basename="store-vat-summaries")
router.register("vat-returns", VATReturnViewSet, basename="vat-returns")
router.register("vat-adjustments", VATAdjustmentViewSet, basename="vat-adjustments")
router.register("tax-payments", TaxPaymentViewSet, basename="tax-payments")

urlpatterns = [
    path("", include(router.urls)),
]