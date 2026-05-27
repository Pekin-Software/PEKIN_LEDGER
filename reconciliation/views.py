from decimal import Decimal

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, ValidationError

from stores.models import Store, StoreUserAssignment

from .models import (
    CashTransaction,
    CashReconciliation,
    MobileMoneyTransaction,
    MobileMoneyReconciliation,
    SupplierVATTransaction,
    SupplierVATReconciliation,
    ReconciliationException
)

from .serializers import (
    CashTransactionSerializer,
    CashReconciliationSerializer,
    MobileMoneyTransactionSerializer,
    MobileMoneyReconciliationSerializer,
    SupplierVATTransactionSerializer,
    SupplierVATReconciliationSerializer,
    ReconciliationExceptionSerializer
)

from .services.services import (
    reconcile_cash,
    reconcile_mobile_money_transaction,
    create_supplier_vat_transaction,
    reconcile_supplier_vat_transaction
)

from .services.dashboard_service import (
    ReconciliationDashboardService
)


class ReconciliationViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    STORE_ALLOWED_ROLES = [
        "Manager",
        "Admin",
        "ACCOUNTANT",
        "AUDITOR",
    ]

    MASTER_ALLOWED_ROLES = [
        "Admin",
        "ACCOUNTANT",
        "AUDITOR",
    ]


    
    def get_tenant(self, request):
        return request.tenant

    def get_store(self, request):
        store_id = (
            request.query_params.get("store_id")
            or request.data.get("store_id")
        )

        if not store_id:
            raise ValidationError({
                "store_id": "store_id is required."
            })

        return Store.objects.get(
            id=store_id,
            tenant=self.get_tenant(request),
        )

    def verify_store_permission(
        self,
        request,
        store,
        report_name="store data",
    ):
        user = request.user
        tenant = self.get_tenant(request)

        if user.position == "Cashier":
            raise PermissionDenied(
                f"You are not allowed to access {report_name}."
            )

        if user.position not in self.STORE_ALLOWED_ROLES:
            raise PermissionDenied(
                f"You are not allowed to access {report_name}."
            )

        if user.position == "Manager":
            assignment = StoreUserAssignment.objects.filter(
                tenant=tenant,
                store=store,
                user_id=user.id,
                is_active=True,
            ).first()

            if not assignment:
                raise PermissionDenied(
                    f"You cannot access another store's {report_name}."
                )

        return True

    def verify_master_permission(
        self,
        request,
        report_name="master data",
    ):
        if request.user.position not in self.MASTER_ALLOWED_ROLES:
            raise PermissionDenied(
                f"You are not allowed to access {report_name}."
            )

        return True

    def apply_date_filter(self, queryset, request, field="created_at"):
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        if start_date and end_date:
            queryset = queryset.filter(
                **{
                    f"{field}__date__range": [
                        start_date,
                        end_date,
                    ]
                }
            )

        return queryset

    @action(detail=False, methods=["get"], url_path="store-cash-transactions")
    def store_cash_transactions(self, request):
        store = self.get_store(request)

        self.verify_store_permission(
            request,
            store,
            "store cash transactions",
        )

        queryset = CashTransaction.objects.filter(
            tenant=self.get_tenant(request),
            store=store,
        )

        queryset = self.apply_date_filter(
            queryset,
            request,
            field="created_at",
        )

        return Response(
            CashTransactionSerializer(
                queryset,
                many=True,
            ).data
        )

    @action(detail=False, methods=["get"], url_path="master-cash-transactions")
    def master_cash_transactions(self, request):
        self.verify_master_permission(
            request,
            "master cash transactions",
        )

        queryset = CashTransaction.objects.filter(
            tenant=self.get_tenant(request),
        )

        queryset = self.apply_date_filter(
            queryset,
            request,
            field="created_at",
        )

        return Response(
            CashTransactionSerializer(
                queryset,
                many=True,
            ).data
        )

    @action(detail=False, methods=["post"], url_path="store-cash-reconcile")
    def store_cash_reconcile(self, request):
        store = self.get_store(request)

        self.verify_store_permission(
            request,
            store,
            "store cash reconciliation",
        )

        counted_cash = request.data.get("counted_cash")

        if counted_cash is None:
            raise ValidationError({
                "counted_cash": "counted_cash is required."
            })

        reconciliation = reconcile_cash(
            tenant=self.get_tenant(request),
            store=store,
            user=request.user,
            counted_cash=Decimal(str(counted_cash)),
            opening_cash=Decimal(
                str(request.data.get("opening_cash", "0.00"))
            ),
            cashier=request.user,
            shift_reference=request.data.get("shift_reference"),
            start_date=request.data.get("start_date"),
            end_date=request.data.get("end_date"),
        )

        return Response(
            CashReconciliationSerializer(reconciliation).data
        )

    @action(detail=False, methods=["get"], url_path="store-cash-reconciliations")
    def store_cash_reconciliations(self, request):
        store = self.get_store(request)

        self.verify_store_permission(
            request,
            store,
            "store cash reconciliations",
        )

        queryset = CashReconciliation.objects.filter(
            tenant=self.get_tenant(request),
            store=store,
        )

        return Response(
            CashReconciliationSerializer(
                queryset,
                many=True,
            ).data
        )

    @action(detail=False, methods=["get"], url_path="master-cash-reconciliations")
    def master_cash_reconciliations(self, request):
        self.verify_master_permission(
            request,
            "master cash reconciliations",
        )

        queryset = CashReconciliation.objects.filter(
            tenant=self.get_tenant(request),
        )

        return Response(
            CashReconciliationSerializer(
                queryset,
                many=True,
            ).data
        )

    @action(detail=False, methods=["get"], url_path="store-mobile-transactions")
    def store_mobile_transactions(self, request):
        store = self.get_store(request)

        self.verify_store_permission(
            request,
            store,
            "store mobile money transactions",
        )

        queryset = MobileMoneyTransaction.objects.filter(
            tenant=self.get_tenant(request),
            store=store,
        )

        return Response(
            MobileMoneyTransactionSerializer(
                queryset,
                many=True,
            ).data
        )

    @action(detail=False, methods=["get"], url_path="master-mobile-transactions")
    def master_mobile_transactions(self, request):
        self.verify_master_permission(
            request,
            "master mobile money transactions",
        )

        queryset = MobileMoneyTransaction.objects.filter(
            tenant=self.get_tenant(request),
        )

        return Response(
            MobileMoneyTransactionSerializer(
                queryset,
                many=True,
            ).data
        )

    @action(detail=False, methods=["post"], url_path="store-mobile-reconcile")
    def store_mobile_reconcile(self, request):
        store = self.get_store(request)

        self.verify_store_permission(
            request,
            store,
            "store mobile money reconciliation",
        )

        momo_transaction_id = request.data.get("momo_transaction_id")
        sale_id = request.data.get("sale_id")

        if not momo_transaction_id:
            raise ValidationError({
                "momo_transaction_id": "momo_transaction_id is required."
            })

        if not sale_id:
            raise ValidationError({
                "sale_id": "sale_id is required."
            })

        reconciliation = reconcile_mobile_money_transaction(
            momo_transaction_id=momo_transaction_id,
            sale_id=sale_id,
            user=request.user,
            tenant=self.get_tenant(request),
            store=store,
        )

        return Response(
            MobileMoneyReconciliationSerializer(reconciliation).data
        )

    @action(detail=False, methods=["get"], url_path="store-mobile-reconciliations")
    def store_mobile_reconciliations(self, request):
        store = self.get_store(request)

        self.verify_store_permission(
            request,
            store,
            "store mobile money reconciliations",
        )

        queryset = MobileMoneyReconciliation.objects.filter(
            tenant=self.get_tenant(request),
            store=store,
        )

        return Response(
            MobileMoneyReconciliationSerializer(
                queryset,
                many=True,
            ).data
        )

    @action(detail=False, methods=["get"], url_path="master-mobile-reconciliations")
    def master_mobile_reconciliations(self, request):
        self.verify_master_permission(
            request,
            "master mobile money reconciliations",
        )

        queryset = MobileMoneyReconciliation.objects.filter(
            tenant=self.get_tenant(request),
        )

        return Response(
            MobileMoneyReconciliationSerializer(
                queryset,
                many=True,
            ).data
        )

    @action(detail=False, methods=["post"], url_path="store-supplier-vat-transaction")
    def store_supplier_vat_transaction(self, request):
        store = self.get_store(request)

        self.verify_store_permission(
            request,
            store,
            "store supplier VAT transaction",
        )

        purchase_id = request.data.get("purchase_id")
        supplier_vat_amount = request.data.get("supplier_vat_amount")

        if not purchase_id:
            raise ValidationError({
                "purchase_id": "purchase_id is required."
            })

        if supplier_vat_amount is None:
            raise ValidationError({
                "supplier_vat_amount": "supplier_vat_amount is required."
            })

        transaction = create_supplier_vat_transaction(
            purchase_id=purchase_id,
            supplier_vat_amount=Decimal(str(supplier_vat_amount)),
            tenant=self.get_tenant(request),
            store=store,
        )

        return Response(
            SupplierVATTransactionSerializer(transaction).data
        )

    @action(detail=False, methods=["get"], url_path="store-supplier-vat-transactions")
    def store_supplier_vat_transactions(self, request):
        store = self.get_store(request)

        self.verify_store_permission(
            request,
            store,
            "store supplier VAT transactions",
        )

        queryset = SupplierVATTransaction.objects.filter(
            tenant=self.get_tenant(request),
            store=store,
        )

        return Response(
            SupplierVATTransactionSerializer(
                queryset,
                many=True,
            ).data
        )

    @action(detail=False, methods=["get"], url_path="master-supplier-vat-transactions")
    def master_supplier_vat_transactions(self, request):
        self.verify_master_permission(
            request,
            "master supplier VAT transactions",
        )

        queryset = SupplierVATTransaction.objects.filter(
            tenant=self.get_tenant(request),
        )

        return Response(
            SupplierVATTransactionSerializer(
                queryset,
                many=True,
            ).data
        )

    @action(detail=False, methods=["post"], url_path="store-supplier-vat-reconcile")
    def store_supplier_vat_reconcile(self, request):
        store = self.get_store(request)

        self.verify_store_permission(
            request,
            store,
            "store supplier VAT reconciliation",
        )

        supplier_vat_transaction_id = request.data.get(
            "supplier_vat_transaction_id"
        )

        if not supplier_vat_transaction_id:
            raise ValidationError({
                "supplier_vat_transaction_id": (
                    "supplier_vat_transaction_id is required."
                )
            })

        reconciliation = reconcile_supplier_vat_transaction(
            supplier_vat_transaction_id=supplier_vat_transaction_id,
            user=request.user,
            tenant=self.get_tenant(request),
            store=store,
        )

        return Response(
            SupplierVATReconciliationSerializer(reconciliation).data
        )

    @action(detail=False, methods=["get"], url_path="store-supplier-vat-reconciliations")
    def store_supplier_vat_reconciliations(self, request):
        store = self.get_store(request)

        self.verify_store_permission(
            request,
            store,
            "store supplier VAT reconciliations",
        )

        queryset = SupplierVATReconciliation.objects.filter(
            tenant=self.get_tenant(request),
            store=store,
        )

        return Response(
            SupplierVATReconciliationSerializer(
                queryset,
                many=True,
            ).data
        )

    @action(detail=False, methods=["get"], url_path="master-supplier-vat-reconciliations")
    def master_supplier_vat_reconciliations(self, request):
        self.verify_master_permission(
            request,
            "master supplier VAT reconciliations",
        )

        queryset = SupplierVATReconciliation.objects.filter(
            tenant=self.get_tenant(request),
        )

        return Response(
            SupplierVATReconciliationSerializer(
                queryset,
                many=True,
            ).data
        )

    @action(detail=False, methods=["get"], url_path="store-exceptions")
    def store_exceptions(self, request):
        store = self.get_store(request)

        self.verify_store_permission(
            request,
            store,
            "store reconciliation exceptions",
        )

        queryset = ReconciliationException.objects.filter(
            tenant=self.get_tenant(request),
            store=store,
        )

        return Response(
            ReconciliationExceptionSerializer(
                queryset,
                many=True,
            ).data
        )

    @action(detail=False, methods=["get"], url_path="master-exceptions")
    def master_exceptions(self, request):
        self.verify_master_permission(
            request,
            "master reconciliation exceptions",
        )

        queryset = ReconciliationException.objects.filter(
            tenant=self.get_tenant(request),
        )

        return Response(
            ReconciliationExceptionSerializer(
                queryset,
                many=True,
            ).data
        )

    @action(detail=False, methods=["get"], url_path="store-dashboard")
    def store_dashboard(self, request):
        store = self.get_store(request)

        self.verify_store_permission(
            request,
            store,
            "store reconciliation dashboard",
        )

        data = ReconciliationDashboardService.generate_dashboard(
            tenant=self.get_tenant(request),
            store=store,
        )

        return Response(data)

    @action(detail=False, methods=["get"], url_path="master-dashboard")
    def master_dashboard(self, request):
        self.verify_master_permission(
            request,
            "master reconciliation dashboard",
        )

        data = ReconciliationDashboardService.generate_dashboard(
            tenant=self.get_tenant(request),
            store=None,
        )

        return Response(data)