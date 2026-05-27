from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import Coalesce

from ledger.models import JournalLine


class CashFlowService:

    CASH_ACCOUNT_PREFIXES = {
        "cash_on_hand": "100",
        "bank": "101",
        "mobile_money": "102",
        "petty_cash": "103",
        "pos_clearing": "104",
    }

    NON_CASH_EXPENSE_ACCOUNTS = [
        "Depreciation",
        "Bad Debt",
        "Amortization",
    ]

    @staticmethod
    def _sum_cash(queryset):
        totals = queryset.aggregate(
            debit_total=Coalesce(Sum("debit"), Decimal("0.00")),
            credit_total=Coalesce(Sum("credit"), Decimal("0.00")),
        )

        return totals["debit_total"] - totals["credit_total"]

    @staticmethod
    def _base_cash_queryset(tenant, store=None):
        prefixes = tuple(
            CashFlowService.CASH_ACCOUNT_PREFIXES.values()
        )

        queryset = JournalLine.objects.filter(
            journal_entry__tenant=tenant,
            journal_entry__status="POSTED",
            account__account_type="ASSET",
            account__code__startswith=prefixes,
        )

        if store:
            queryset = queryset.filter(
                store=store
            )

        return queryset

    @staticmethod
    def _apply_date_range(queryset, start_date=None, end_date=None):
        if start_date:
            queryset = queryset.filter(
                journal_entry__entry_date__gte=start_date
            )

        if end_date:
            queryset = queryset.filter(
                journal_entry__entry_date__lte=end_date
            )

        return queryset

    @staticmethod
    def _get_category_cash_flow(queryset, category):
        return CashFlowService._sum_cash(
            queryset.filter(
                journal_entry__cash_flow_category=category
            )
        )

    @staticmethod
    def _get_uncategorized_cash_flow(queryset):
        return CashFlowService._sum_cash(
            queryset.filter(
                journal_entry__cash_flow_category__isnull=True
            )
        )

    @staticmethod
    def _get_liquidity_breakdown(queryset):
        breakdown = {}

        for name, prefix in CashFlowService.CASH_ACCOUNT_PREFIXES.items():
            account_queryset = queryset.filter(
                account__code__startswith=prefix
            )

            breakdown[name] = CashFlowService._sum_cash(
                account_queryset
            )

        return breakdown

    @staticmethod
    def _get_reconciliation_summary(queryset):
        reconciled_cash = CashFlowService._sum_cash(
            queryset.filter(
                journal_entry__is_reconciled=True
            )
        )

        unreconciled_cash = CashFlowService._sum_cash(
            queryset.filter(
                journal_entry__is_reconciled=False
            )
        )

        return {
            "reconciled_cash": reconciled_cash,
            "unreconciled_cash": unreconciled_cash,
        }

    @staticmethod
    def _get_non_cash_adjustments(tenant, store=None, start_date=None, end_date=None):
        queryset = JournalLine.objects.filter(
            journal_entry__tenant=tenant,
            journal_entry__status="POSTED",
            account__account_type="EXPENSE",
        )

        if store:
            queryset = queryset.filter(
                store=store
            )

        queryset = CashFlowService._apply_date_range(
            queryset,
            start_date,
            end_date
        )

        non_cash_queryset = queryset.filter(
            account__name__icontains="Depreciation"
        ) | queryset.filter(
            account__name__icontains="Bad Debt"
        ) | queryset.filter(
            account__name__icontains="Amortization"
        )

        totals = non_cash_queryset.aggregate(
            debit_total=Coalesce(Sum("debit"), Decimal("0.00")),
            credit_total=Coalesce(Sum("credit"), Decimal("0.00")),
        )

        return totals["debit_total"] - totals["credit_total"]

    @staticmethod
    def generate_cash_flow_statement(
        tenant,
        start_date=None,
        end_date=None,
        store=None
    ):
        period_queryset = CashFlowService._base_cash_queryset(
            tenant=tenant,
            store=store
        )

        period_queryset = CashFlowService._apply_date_range(
            period_queryset,
            start_date,
            end_date
        )

        opening_queryset = CashFlowService._base_cash_queryset(
            tenant=tenant,
            store=store
        )

        if start_date:
            opening_queryset = opening_queryset.filter(
                journal_entry__entry_date__lt=start_date
            )

        opening_cash_balance = CashFlowService._sum_cash(
            opening_queryset
        )

        operating_cash_flow = CashFlowService._get_category_cash_flow(
            period_queryset,
            "OPERATING"
        )

        investing_cash_flow = CashFlowService._get_category_cash_flow(
            period_queryset,
            "INVESTING"
        )

        financing_cash_flow = CashFlowService._get_category_cash_flow(
            period_queryset,
            "FINANCING"
        )

        uncategorized_cash_flow = CashFlowService._get_uncategorized_cash_flow(
            period_queryset
        )

        non_cash_adjustments = CashFlowService._get_non_cash_adjustments(
            tenant=tenant,
            store=store,
            start_date=start_date,
            end_date=end_date
        )

        indirect_operating_cash_flow = (
            operating_cash_flow + non_cash_adjustments
        )

        net_cash_flow = (
            operating_cash_flow
            + investing_cash_flow
            + financing_cash_flow
            + uncategorized_cash_flow
        )

        closing_cash_balance = opening_cash_balance + net_cash_flow

        liquidity_breakdown = CashFlowService._get_liquidity_breakdown(
            period_queryset
        )

        reconciliation_summary = CashFlowService._get_reconciliation_summary(
            period_queryset
        )

        return {
            "tenant": tenant.id,
            "store": store.id if store else "CONSOLIDATED",
            "start_date": start_date,
            "end_date": end_date,

            "opening_cash_balance": opening_cash_balance,

            "direct_method": {
                "operating_cash_flow": operating_cash_flow,
                "investing_cash_flow": investing_cash_flow,
                "financing_cash_flow": financing_cash_flow,
                "uncategorized_cash_flow": uncategorized_cash_flow,
                "net_cash_flow": net_cash_flow,
            },

            "indirect_method_support": {
                "operating_cash_flow_before_adjustments": operating_cash_flow,
                "non_cash_adjustments": non_cash_adjustments,
                "adjusted_operating_cash_flow": indirect_operating_cash_flow,
            },

            "liquidity_breakdown": liquidity_breakdown,

            "reconciliation_summary": reconciliation_summary,

            "closing_cash_balance": closing_cash_balance,
        }

    @staticmethod
    def generate_multi_store_cash_flow_statement(
        tenant,
        stores,
        start_date=None,
        end_date=None
    ):
        store_reports = []

        total_opening_cash = Decimal("0.00")
        total_operating_cash_flow = Decimal("0.00")
        total_investing_cash_flow = Decimal("0.00")
        total_financing_cash_flow = Decimal("0.00")
        total_uncategorized_cash_flow = Decimal("0.00")
        total_net_cash_flow = Decimal("0.00")
        total_closing_cash = Decimal("0.00")
        total_non_cash_adjustments = Decimal("0.00")

        for store in stores:
            report = CashFlowService.generate_cash_flow_statement(
                tenant=tenant,
                store=store,
                start_date=start_date,
                end_date=end_date
            )

            store_reports.append(report)

            total_opening_cash += report["opening_cash_balance"]
            total_operating_cash_flow += report["direct_method"]["operating_cash_flow"]
            total_investing_cash_flow += report["direct_method"]["investing_cash_flow"]
            total_financing_cash_flow += report["direct_method"]["financing_cash_flow"]
            total_uncategorized_cash_flow += report["direct_method"]["uncategorized_cash_flow"]
            total_net_cash_flow += report["direct_method"]["net_cash_flow"]
            total_closing_cash += report["closing_cash_balance"]
            total_non_cash_adjustments += report["indirect_method_support"]["non_cash_adjustments"]

        return {
            "tenant": tenant.id,
            "start_date": start_date,
            "end_date": end_date,
            "stores": store_reports,
            "consolidated": {
                "opening_cash_balance": total_opening_cash,
                "operating_cash_flow": total_operating_cash_flow,
                "investing_cash_flow": total_investing_cash_flow,
                "financing_cash_flow": total_financing_cash_flow,
                "uncategorized_cash_flow": total_uncategorized_cash_flow,
                "non_cash_adjustments": total_non_cash_adjustments,
                "net_cash_flow": total_net_cash_flow,
                "closing_cash_balance": total_closing_cash,
            }
        }