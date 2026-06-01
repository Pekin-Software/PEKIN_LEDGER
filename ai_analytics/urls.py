from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ComplianceAlertViewSet,
    ComplianceRiskProfileViewSet,
    ComplianceAnalysisRunViewSet,
    ComplianceIntelligenceViewSet
)


router = DefaultRouter()

router.register(
    r'compliance-alerts',
    ComplianceAlertViewSet,
    basename='compliance-alerts'
)

router.register(
    r'compliance-risk-profiles',
    ComplianceRiskProfileViewSet,
    basename='compliance-risk-profiles'
)

router.register(
    r'compliance-analysis-runs',
    ComplianceAnalysisRunViewSet,
    basename='compliance-analysis-runs'
)

router.register(
    r'compliance-intelligence',
    ComplianceIntelligenceViewSet,
    basename='compliance-intelligence'
)