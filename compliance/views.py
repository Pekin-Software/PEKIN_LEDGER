from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from stores.models import Store

from .models import (
    PeriodLock,
    TaxFiling,
    ComplianceAuditLog,
    BranchVATSummary,
    POSComplianceEvent,
    InventoryComplianceEvent,
)

from .serializers import (
    PeriodLockSerializer,
    TaxFilingSerializer,
    ComplianceAuditLogSerializer,
    BranchVATSummarySerializer,
    POSComplianceEventSerializer,
    InventoryComplianceEventSerializer,
)

from permissions import ComplianceAccessMixin

from .services import (
    lock_reporting_period,
    generate_vat_filing,
    generate_branch_vat_summary,
    approve_tax_filing,
    submit_tax_filing_to_lra,
)


class ComplianceViewSet(ComplianceAccessMixin, viewsets.ViewSet):

    permission_classes = [IsAuthenticated]

    def get_store(self, request):
        store_id = request.query_params.get("store_id") or request.data.get("store_id")

        if not store_id:
            return None

        return Store.objects.get(
            id=store_id,
            tenant=self.get_tenant(request)
        )

    def apply_date_filter(self, queryset, request):
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)

        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)

        return queryset

    def apply_generated_date_filter(self, queryset, request):
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        if start_date:
            queryset = queryset.filter(generated_at__date__gte=start_date)

        if end_date:
            queryset = queryset.filter(generated_at__date__lte=end_date)

        return queryset

    # ======================================================
    # GET DASHBOARD / MONITORING ENDPOINTS
    # ======================================================

    @action(detail=False, methods=["get"], url_path="store-vat-summary")
    def store_vat_summary(self, request):
        store = self.get_store(request)

        if not store:
            return Response(
                {"error": "store_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        self.verify_store_permission(
            request,
            store,
            resource_name="store VAT summary"
        )

        queryset = BranchVATSummary.objects.filter(
            tenant=self.get_tenant(request),
            store=store
        ).order_by("-reporting_period")

        queryset = self.apply_generated_date_filter(queryset, request)

        return Response(
            BranchVATSummarySerializer(queryset, many=True).data
        )

    @action(detail=False, methods=["get"], url_path="master-vat-summary")
    def master_vat_summary(self, request):
        self.verify_master_permission(
            request,
            resource_name="master VAT summary"
        )

        queryset = BranchVATSummary.objects.filter(
            tenant=self.get_tenant(request)
        ).order_by("-reporting_period")

        queryset = self.apply_generated_date_filter(queryset, request)

        return Response(
            BranchVATSummarySerializer(queryset, many=True).data
        )

    @action(detail=False, methods=["get"], url_path="store-audit-logs")
    def store_audit_logs(self, request):
        store = self.get_store(request)

        if not store:
            return Response(
                {"error": "store_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        self.verify_store_permission(
            request,
            store,
            resource_name="store audit logs"
        )

        queryset = ComplianceAuditLog.objects.filter(
            tenant=self.get_tenant(request),
            store=store
        ).order_by("-created_at")

        queryset = self.apply_date_filter(queryset, request)

        return Response(
            ComplianceAuditLogSerializer(queryset, many=True).data
        )

    @action(detail=False, methods=["get"], url_path="master-audit-logs")
    def master_audit_logs(self, request):
        self.verify_master_permission(
            request,
            resource_name="master audit logs"
        )

        queryset = ComplianceAuditLog.objects.filter(
            tenant=self.get_tenant(request)
        ).order_by("-created_at")

        queryset = self.apply_date_filter(queryset, request)

        return Response(
            ComplianceAuditLogSerializer(queryset, many=True).data
        )

    @action(detail=False, methods=["get"], url_path="store-pos-events")
    def store_pos_events(self, request):
        store = self.get_store(request)

        if not store:
            return Response(
                {"error": "store_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        self.verify_store_permission(
            request,
            store,
            resource_name="store POS events"
        )

        queryset = POSComplianceEvent.objects.filter(
            tenant=self.get_tenant(request),
            store=store
        ).order_by("-created_at")

        queryset = self.apply_date_filter(queryset, request)

        return Response(
            POSComplianceEventSerializer(queryset, many=True).data
        )

    @action(detail=False, methods=["get"], url_path="store-inventory-events")
    def store_inventory_events(self, request):
        store = self.get_store(request)

        if not store:
            return Response(
                {"error": "store_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        self.verify_store_permission(
            request,
            store,
            resource_name="store inventory events"
        )

        queryset = InventoryComplianceEvent.objects.filter(
            tenant=self.get_tenant(request),
            store=store
        ).order_by("-created_at")

        queryset = self.apply_date_filter(queryset, request)

        return Response(
            InventoryComplianceEventSerializer(queryset, many=True).data
        )

    @action(detail=False, methods=["get"], url_path="store-vat-filings")
    def store_vat_filings(self, request):
        store = self.get_store(request)

        if not store:
            return Response(
                {"error": "store_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        self.verify_store_permission(
            request,
            store,
            resource_name="store VAT filings"
        )

        queryset = TaxFiling.objects.filter(
            tenant=self.get_tenant(request),
            store=store,
            tax_type="VAT"
        ).order_by("-created_at")

        queryset = self.apply_date_filter(queryset, request)

        return Response(
            TaxFilingSerializer(queryset, many=True).data
        )

    @action(detail=False, methods=["get"], url_path="master-vat-filings")
    def master_vat_filings(self, request):
        self.verify_master_permission(
            request,
            resource_name="master VAT filings"
        )

        queryset = TaxFiling.objects.filter(
            tenant=self.get_tenant(request),
            store__isnull=True,
            tax_type="VAT"
        ).order_by("-created_at")

        queryset = self.apply_date_filter(queryset, request)

        return Response(
            TaxFilingSerializer(queryset, many=True).data
        )

    @action(detail=False, methods=["get"], url_path="store-periodlocks")
    def store_periodlocks(self, request):
        store = self.get_store(request)

        if not store:
            return Response(
                {"error": "store_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        self.verify_store_permission(
            request,
            store,
            resource_name="store period locks"
        )

        queryset = PeriodLock.objects.filter(
            tenant=self.get_tenant(request),
            store=store
        ).order_by("-locked_at")

        return Response(
            PeriodLockSerializer(queryset, many=True).data
        )

    @action(detail=False, methods=["get"], url_path="master-periodlocks")
    def master_periodlocks(self, request):
        self.verify_master_permission(
            request,
            resource_name="master period locks"
        )

        queryset = PeriodLock.objects.filter(
            tenant=self.get_tenant(request),
            store__isnull=True
        ).order_by("-locked_at")

        return Response(
            PeriodLockSerializer(queryset, many=True).data
        )

    # ======================================================
    # POST CONTROLLED ACTION ENDPOINTS
    # ======================================================

    @action(detail=False, methods=["post"], url_path="lock-store-period")
    def lock_store_period(self, request):
        store = self.get_store(request)

        if not store:
            return Response(
                {"error": "store_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        self.verify_store_permission(
            request,
            store,
            resource_name="store period lock"
        )

        reporting_period = request.data.get("reporting_period")
        lock_type = request.data.get("lock_type", "FULL")
        reason = request.data.get("reason")

        if not reporting_period:
            return Response(
                {"error": "reporting_period is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        period_lock = lock_reporting_period(
            tenant=self.get_tenant(request),
            store=store,
            reporting_period=reporting_period,
            lock_type=lock_type,
            user=request.user,
            reason=reason
        )

        return Response(
            PeriodLockSerializer(period_lock).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=["post"], url_path="lock-master-period")
    def lock_master_period(self, request):
        self.verify_master_permission(
            request,
            resource_name="master period lock"
        )

        reporting_period = request.data.get("reporting_period")
        lock_type = request.data.get("lock_type", "FULL")
        reason = request.data.get("reason")

        if not reporting_period:
            return Response(
                {"error": "reporting_period is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        period_lock = lock_reporting_period(
            tenant=self.get_tenant(request),
            store=None,
            reporting_period=reporting_period,
            lock_type=lock_type,
            user=request.user,
            reason=reason
        )

        return Response(
            PeriodLockSerializer(period_lock).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=["post"], url_path="regenerate-store-vat-summary")
    def regenerate_store_vat_summary(self, request):
        store = self.get_store(request)

        if not store:
            return Response(
                {"error": "store_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        self.verify_store_permission(
            request,
            store,
            resource_name="store VAT summary regeneration"
        )

        reporting_period = request.data.get("reporting_period")

        if not reporting_period:
            return Response(
                {"error": "reporting_period is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        summary = generate_branch_vat_summary(
            tenant=self.get_tenant(request),
            store=store,
            reporting_period=reporting_period
        )

        return Response(
            BranchVATSummarySerializer(summary).data,
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["post"], url_path="regenerate-store-vat-filing")
    def regenerate_store_vat_filing(self, request):
        store = self.get_store(request)

        if not store:
            return Response(
                {"error": "store_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        self.verify_store_permission(
            request,
            store,
            resource_name="store VAT filing regeneration"
        )

        reporting_period = request.data.get("reporting_period")

        if not reporting_period:
            return Response(
                {"error": "reporting_period is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        filing = generate_vat_filing(
            tenant=self.get_tenant(request),
            store=store,
            reporting_period=reporting_period,
            user=request.user
        )

        return Response(
            TaxFilingSerializer(filing).data,
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["post"], url_path="regenerate-master-vat-filing")
    def regenerate_master_vat_filing(self, request):
        self.verify_master_permission(
            request,
            resource_name="master VAT filing regeneration"
        )

        reporting_period = request.data.get("reporting_period")

        if not reporting_period:
            return Response(
                {"error": "reporting_period is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        filing = generate_vat_filing(
            tenant=self.get_tenant(request),
            store=None,
            reporting_period=reporting_period,
            user=request.user
        )

        return Response(
            TaxFilingSerializer(filing).data,
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["post"], url_path="approve-vat-filing")
    def approve_vat_filing(self, request):
        self.verify_master_permission(
            request,
            resource_name="VAT filing approval"
        )

        filing_id = request.data.get("filing_id")

        if not filing_id:
            return Response(
                {"error": "filing_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        filing = TaxFiling.objects.get(
            id=filing_id,
            tenant=self.get_tenant(request)
        )

        approved_filing = approve_tax_filing(
            filing_id=filing.id,
            user=request.user
        )

        return Response(
            TaxFilingSerializer(approved_filing).data,
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["post"], url_path="submit-vat-filing")
    def submit_vat_filing(self, request):
        self.verify_master_permission(
            request,
            resource_name="VAT filing submission"
        )

        filing_id = request.data.get("filing_id")

        if not filing_id:
            return Response(
                {"error": "filing_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        filing = TaxFiling.objects.get(
            id=filing_id,
            tenant=self.get_tenant(request)
        )

        submitted_filing = submit_tax_filing_to_lra(
            filing_id=filing.id,
            user=request.user
        )

        return Response(
            TaxFilingSerializer(submitted_filing).data,
            status=status.HTTP_200_OK
        )