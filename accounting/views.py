from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError, PermissionDenied

from accounting.services.trial_balance_service import TrialBalanceService
from accounting.services.profit_loss_service import ProfitLossService
from accounting.services.balance_sheet_service import BalanceSheetService
from accounting.services.cash_flow_service import CashFlowService
from accounting.services.general_ledger_service import GeneralLedgerService
from stores.models import Store, StoreUserAssignment


class FinancialReportViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def get_tenant(self, request):
        return request.user.domain

    def get_date_range(self, request):
        return {
            "start_date": request.GET.get("start_date"),
            "end_date": request.GET.get("end_date"),
        }

    def get_store(self, request):
        tenant = self.get_tenant(request)
        store_id = request.query_params.get("store_id")

        if not store_id:
            raise ValidationError({
                "store_id": "store_id is required."
            })

        try:
            return Store.objects.get(
                id=store_id,
                tenant=tenant
            )

        except Store.DoesNotExist:
            raise ValidationError({
                "store_id": "Invalid store for this tenant."
            })

    def verify_store_report_permission(self, request, store, report_name="report"):
        user = request.user
        tenant = self.get_tenant(request)

        if user.position == "Cashier":
            raise PermissionDenied(
                f"You are not allowed to access {report_name} reports."
            )

        if user.position == "Manager":
            assignment = StoreUserAssignment.objects.filter(
                tenant=tenant,
                store=store,
                user_id=user.id,
                is_active=True
            ).first()

            if not assignment:
                raise PermissionDenied(
                    f"You cannot access another store's {report_name}."
                )

        return True

    def verify_master_report_permission(self, request, report_name="master report"):
        user = request.user

        allowed_roles = [
            "Admin",
            "ACCOUNTANT",
            "AUDITOR",
        ]

        if user.position not in allowed_roles:
            raise PermissionDenied(
                f"You are not allowed to access {report_name}."
            )

        return True
    
    
    @action(detail=False, methods=["get"], url_path="trial-balance")
    def trial_balance(self, request):
        dates = self.get_date_range(request)
        tenant = self.get_tenant(request)
        store = self.get_store(request)

        self.verify_store_report_permission(
            request=request,
            store=store,
            report_name="trial balance"
        )

        report = TrialBalanceService.generate_trial_balance(
            tenant=tenant,
            store=store,
            start_date=dates["start_date"],
            end_date=dates["end_date"],
            adjusted=True,
        )

        return Response(report)

    @action(detail=False, methods=["get"], url_path="master-trial-balance")
    def master_trial_balance(self, request):
        dates = self.get_date_range(request)
        tenant = self.get_tenant(request)

        self.verify_master_report_permission(
            request=request,
            report_name="master trial balance"
        )

        report = TrialBalanceService.generate_master_trial_balance(
            tenant=tenant,
            start_date=dates["start_date"],
            end_date=dates["end_date"],
        )

        return Response(report)

    @action(detail=False, methods=["get"], url_path="store-p-and-l")
    def store_profit_and_loss(self, request):
        dates = self.get_date_range(request)
        tenant = self.get_tenant(request)
        store = self.get_store(request)

        self.verify_store_report_permission(
            request=request,
            store=store,
            report_name="profit and loss"
        )

        report = ProfitLossService.generate_profit_and_loss(
            tenant=tenant,
            store=store,
            start_date=dates["start_date"],
            end_date=dates["end_date"],
        )

        return Response(report)

    @action(detail=False, methods=["get"], url_path="master-p-and-l")
    def master_profit_and_loss(self, request):
        dates = self.get_date_range(request)
        tenant = self.get_tenant(request)

        self.verify_master_report_permission(
            request=request,
            report_name="consolidated profit and loss"
        )

        report = ProfitLossService.generate_profit_and_loss(
            tenant=tenant,
            start_date=dates["start_date"],
            end_date=dates["end_date"],
        )

        return Response(report)

    @action(detail=False,methods=["get"],url_path="store-balance-sheet")
    def store_balance_sheet(self, request):
        tenant = self.get_tenant(request)
        dates = self.get_date_range(request)
        store = self.get_store(request)

        self.verify_store_report_permission(
            request=request,
            store=store,
            report_name="balance sheet"
        )

        report = BalanceSheetService.generate_balance_sheet(
            tenant=tenant,
            store=store,
            start_date=dates["start_date"],
            end_date=dates["end_date"],
            adjusted=True
        )

        return Response(report)

    @action(detail=False, methods=["get"], url_path="master-balance-sheet")
    def master_balance_sheet(self, request):
        tenant = self.get_tenant(request)
        dates = self.get_date_range(request)

        self.verify_master_report_permission(
            request=request,
            report_name="master balance sheet"
        )

        report = BalanceSheetService.generate_balance_sheet(
            tenant=tenant,
            store=None,
            start_date=dates["start_date"],
            end_date=dates["end_date"],
            adjusted=True
        )

        return Response(report)

    @action(
        detail=False,
        methods=["get"],
        url_path="store-cash-flow"
    )
    def store_cash_flow(self, request):
        tenant = self.get_tenant(request)
        dates = self.get_date_range(request)
        store = self.get_store(request)

        self.verify_store_report_permission(
            request=request,
            store=store,
            report_name="cash flow"
        )

        report = CashFlowService.generate_cash_flow_statement(
            tenant=tenant,
            store=store,
            start_date=dates["start_date"],
            end_date=dates["end_date"],
        )

        return Response(report)

    @action(
        detail=False,
        methods=["get"],
        url_path="master-cash-flow"
    )
    def master_cash_flow(self, request):
        tenant = self.get_tenant(request)
        dates = self.get_date_range(request)

        self.verify_master_report_permission(
            request=request,
            report_name="master cash flow report"
        )

        stores = Store.objects.filter(tenant=tenant)

        report = CashFlowService.generate_multi_store_cash_flow_statement(
            tenant=tenant,
            stores=stores,
            start_date=dates["start_date"],
            end_date=dates["end_date"],
        )

        return Response(report)

    @action(
        detail=False,
        methods=["get"],
        url_path="store-general-ledger"
    )
    def store_general_ledger(self, request):
        dates = self.get_date_range(request)
        tenant = self.get_tenant(request)
        store = self.get_store(request)

        self.verify_store_report_permission(
            request=request,
            store=store,
            report_name="general ledger"
        )

        report = GeneralLedgerService.generate_general_ledger(
            tenant=tenant,
            store=store,
            start_date=dates["start_date"],
            end_date=dates["end_date"],
        )

        return Response({
            "report_type": "STORE_GENERAL_LEDGER",
            "tenant": tenant.id if tenant else None,
            "store": {
                "id": store.id,
                "name": store.name,
            },
            "start_date": dates["start_date"],
            "end_date": dates["end_date"],
            "data": report,
        })

    @action(
        detail=False,
        methods=["get"],
        url_path="master-general-ledger"
    )
    def master_general_ledger(self, request):
        dates = self.get_date_range(request)
        tenant = self.get_tenant(request)

        self.verify_master_report_permission(
            request=request,
            report_name="master general ledger"
        )

        report = GeneralLedgerService.generate_general_ledger(
            tenant=tenant,
            start_date=dates["start_date"],
            end_date=dates["end_date"],
        )

        return Response({
            "report_type": "MASTER_GENERAL_LEDGER",
            "tenant": tenant.id if tenant else None,
            "start_date": dates["start_date"],
            "end_date": dates["end_date"],
            "data": report,
        })



