from decimal import Decimal
from ledger.models import Account
from accounting.services.account_balance_service import AccountBalanceService


class ProfitLossService:

    @staticmethod
    def generate_profit_and_loss(
        tenant,
        store=None,
        start_date=None,
        end_date=None,
        adjusted=True,
        exclude_inter_store=False
    ):
        revenue_accounts = Account.objects.filter(
            tenant=tenant,
            account_type="REVENUE",
            is_active=True
        ).order_by("code")

        expense_accounts = Account.objects.filter(
            tenant=tenant,
            account_type="EXPENSE",
            is_active=True
        ).order_by("code")

        revenues = []
        expenses = []

        total_revenue = Decimal("0.00")
        total_expenses = Decimal("0.00")

        for account in revenue_accounts:
            balance = AccountBalanceService.get_account_balance(
                account=account,
                tenant=tenant,
                store=store,
                start_date=start_date,
                end_date=end_date,
                adjusted=adjusted,
                exclude_inter_store=exclude_inter_store
            )

            if balance == Decimal("0.00"):
                continue

            revenues.append({
                "account_id": account.id,
                "account_code": account.code,
                "account": account.name,
                "amount": balance
            })

            total_revenue += balance

        for account in expense_accounts:
            balance = AccountBalanceService.get_account_balance(
                account=account,
                tenant=tenant,
                store=store,
                start_date=start_date,
                end_date=end_date,
                adjusted=adjusted,
                exclude_inter_store=exclude_inter_store
            )

            if balance == Decimal("0.00"):
                continue

            expenses.append({
                "account_id": account.id,
                "account_code": account.code,
                "account": account.name,
                "amount": balance
            })

            total_expenses += balance

        net_profit = total_revenue - total_expenses

        return {
            "tenant_id": tenant.id,
            "store_id": store.id if store else None,
            "report_type": "BRANCH" if store else "CONSOLIDATED",
            "start_date": start_date,
            "end_date": end_date,
            "revenues": revenues,
            "expenses": expenses,
            "total_revenue": total_revenue,
            "total_expenses": total_expenses,
            "net_profit": net_profit
        }