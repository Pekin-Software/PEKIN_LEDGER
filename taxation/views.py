from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from taxation.models import (
    TaxClass,
    TaxPeriod,
    VATLedger,
    StoreVATSummary,
    VATReturn,
    VATAdjustment,
    TaxPayment,
)

from taxation.serializers import (
    TaxClassSerializer,
    TaxPeriodSerializer,
    VATLedgerSerializer,
    StoreVATSummarySerializer,
    VATReturnSerializer,
    VATAdjustmentSerializer,
    TaxPaymentSerializer,
)

from taxation.permissions import IsAdminOnly, IsAdminOrFinance
from taxation.vat_services import (
    calculate_store_vat_summary,
    submit_store_vat_summary,
    approve_store_vat_summary,
    reject_store_vat_summary,
    generate_consolidated_vat_return,
    approve_vat_return,
    file_vat_return,
    record_vat_payment,
    approve_vat_adjustment,
)


class TaxClassViewSet(viewsets.ModelViewSet):
    serializer_class = TaxClassSerializer
    permission_classes = [IsAuthenticated, IsAdminOrFinance]

    def get_queryset(self):
        return TaxClass.objects.filter(tenant=self.request.user.tenant)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)


class TaxPeriodViewSet(viewsets.ModelViewSet):
    serializer_class = TaxPeriodSerializer
    permission_classes = [IsAuthenticated, IsAdminOrFinance]

    def get_queryset(self):
        return TaxPeriod.objects.filter(tenant=self.request.user.tenant)

    def perform_create(self, serializer):
        serializer.save(
            tenant=self.request.user.tenant,
            created_by=self.request.user
        )


class VATLedgerViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = VATLedgerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = VATLedger.objects.filter(tenant=user.tenant)

        if getattr(user, "role", None) == "STORE_MANAGER":
            queryset = queryset.filter(store=getattr(user, "store", None))

        return queryset


class StoreVATSummaryViewSet(viewsets.ModelViewSet):
    serializer_class = StoreVATSummarySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = StoreVATSummary.objects.filter(tenant=user.tenant)

        if getattr(user, "role", None) == "STORE_MANAGER":
            queryset = queryset.filter(store=getattr(user, "store", None))

        return queryset

    @action(detail=False, methods=["post"], url_path="calculate")
    def calculate(self, request):
        tax_period_id = request.data.get("tax_period_id")
        store_id = request.data.get("store_id")

        tax_period = TaxPeriod.objects.get(
            id=tax_period_id,
            tenant=request.user.tenant
        )

        if getattr(request.user, "role", None) == "STORE_MANAGER":
            store = request.user.store
        else:
            from inventory.models import Store
            store = Store.objects.get(id=store_id, tenant=request.user.tenant)

        summary = calculate_store_vat_summary(
            tenant=request.user.tenant,
            store=store,
            tax_period=tax_period
        )

        return Response(StoreVATSummarySerializer(summary).data)

    @action(detail=True, methods=["post"], url_path="submit")
    def submit(self, request, pk=None):
        summary = self.get_object()
        summary = submit_store_vat_summary(summary, request.user)
        return Response(StoreVATSummarySerializer(summary).data)

    @action(detail=True, methods=["post"], url_path="approve", permission_classes=[IsAuthenticated, IsAdminOrFinance])
    def approve(self, request, pk=None):
        summary = self.get_object()
        summary = approve_store_vat_summary(summary, request.user)
        return Response(StoreVATSummarySerializer(summary).data)

    @action(detail=True, methods=["post"], url_path="reject", permission_classes=[IsAuthenticated, IsAdminOrFinance])
    def reject(self, request, pk=None):
        summary = self.get_object()
        reason = request.data.get("reason")

        if not reason:
            return Response(
                {"detail": "Rejection reason is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        summary = reject_store_vat_summary(summary, request.user, reason)
        return Response(StoreVATSummarySerializer(summary).data)


class VATReturnViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = VATReturnSerializer
    permission_classes = [IsAuthenticated, IsAdminOrFinance]

    def get_queryset(self):
        return VATReturn.objects.filter(tenant=self.request.user.tenant)

    @action(detail=False, methods=["post"], url_path="generate")
    def generate(self, request):
        tax_period_id = request.data.get("tax_period_id")

        tax_period = TaxPeriod.objects.get(
            id=tax_period_id,
            tenant=request.user.tenant
        )

        vat_return = generate_consolidated_vat_return(
            tenant=request.user.tenant,
            tax_period=tax_period
        )

        return Response(VATReturnSerializer(vat_return).data)

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        vat_return = self.get_object()
        vat_return = approve_vat_return(vat_return, request.user)
        return Response(VATReturnSerializer(vat_return).data)

    @action(detail=True, methods=["post"], url_path="file", permission_classes=[IsAuthenticated, IsAdminOnly])
    def file(self, request, pk=None):
        vat_return = self.get_object()
        filing_reference = request.data.get("filing_reference")

        if not filing_reference:
            return Response(
                {"detail": "Filing reference is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        vat_return = file_vat_return(
            vat_return=vat_return,
            user=request.user,
            filing_reference=filing_reference
        )

        return Response(VATReturnSerializer(vat_return).data)

    @action(detail=True, methods=["post"], url_path="record-payment", permission_classes=[IsAuthenticated, IsAdminOnly])
    def record_payment(self, request, pk=None):
        vat_return = self.get_object()

        payment = record_vat_payment(
            vat_return=vat_return,
            user=request.user,
            amount=request.data.get("amount"),
            payment_method=request.data.get("payment_method"),
            transaction_reference=request.data.get("transaction_reference")
        )

        return Response(TaxPaymentSerializer(payment).data)


class VATAdjustmentViewSet(viewsets.ModelViewSet):
    serializer_class = VATAdjustmentSerializer
    permission_classes = [IsAuthenticated, IsAdminOrFinance]

    def get_queryset(self):
        return VATAdjustment.objects.filter(tenant=self.request.user.tenant)

    def perform_create(self, serializer):
        serializer.save(
            tenant=self.request.user.tenant,
            created_by=self.request.user
        )

    @action(detail=True, methods=["post"], url_path="approve", permission_classes=[IsAuthenticated, IsAdminOnly])
    def approve(self, request, pk=None):
        adjustment = self.get_object()
        adjustment = approve_vat_adjustment(adjustment, request.user)
        return Response(VATAdjustmentSerializer(adjustment).data)


class TaxPaymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TaxPaymentSerializer
    permission_classes = [IsAuthenticated, IsAdminOrFinance]

    def get_queryset(self):
        return TaxPayment.objects.filter(tenant=self.request.user.tenant)