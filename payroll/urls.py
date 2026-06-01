from rest_framework.routers import DefaultRouter

from .views import PayrollViewSet, PAYETaxBracketViewSet

router = DefaultRouter()

router.register(
    r'payroll',
    PayrollViewSet,
    basename='payroll'
)

router.register(
    r'paye-tax-brackets',
    PAYETaxBracketViewSet,
    basename='paye-tax-brackets'
)
urlpatterns = router.urls

# GET  /api/payroll/store-employees/?store_id=1
# GET  /api/payroll/master-employees/
# POST /api/payroll/create-payroll/
# GET  /api/payroll/payroll/
# GET  /api/payroll/payroll/?store_id=1
# POST /api/payroll/{id}/approve/
# POST /api/payroll/{id}/reject/
# POST /api/paye-tax-brackets/
# POST /api/payroll/pay-payroll/