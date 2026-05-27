from decimal import Decimal

from ledger.models import Account

from accounting.services.account_balance_service import (
    AccountBalanceService
)

from accounting.services.profit_loss_service import (
    ProfitLossService
)


class BalanceSheetService:
    RETAINED_EARNINGS_CODE = "3200"
    
    @staticmethod
    def generate_balance_sheet(
        tenant,
        store=None,
        start_date=None,
        end_date=None,
        adjusted=True
    ):
        assets = []
        liabilities = []
        equity = []

        total_assets = Decimal("0.00")
        total_liabilities = Decimal("0.00")
        total_equity = Decimal("0.00")

        is_consolidated = store is None
        exclude_inter_store = is_consolidated

        account_groups = {
            "assets": Account.objects.filter(
                tenant=tenant,
                account_type="ASSET",
                is_active=True
            ).order_by("code"),

            "liabilities": Account.objects.filter(
                tenant=tenant,
                account_type="LIABILITY",
                is_active=True
            ).order_by("code"),

            "equity": Account.objects.filter(
                tenant=tenant,
                account_type="EQUITY",
                is_active=True
            ).order_by("code"),
        }


        for account in account_groups["assets"]:
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

            assets.append({
                "account_id": account.id,
                "account_code": account.code,
                "account": account.name,
                "amount": balance
            })

            total_assets += balance

        for account in account_groups["liabilities"]:
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

            liabilities.append({
                "account_id": account.id,
                "account_code": account.code,
                "account": account.name,
                "amount": balance
            })

            total_liabilities += balance

        retained_earnings = None

        for account in account_groups["equity"]:
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

            if account.code == BalanceSheetService.RETAINED_EARNINGS_CODE:
                retained_earnings = {
                    "account_id": account.id,
                    "account_code": account.code,
                    "account": account.name,
                    "amount": balance
                }
                total_equity += balance
                continue

            equity.append({
                "account_id": account.id,
                "account_code": account.code,
                "account": account.name,
                "amount": balance
            })

            total_equity += balance

        pnl = ProfitLossService.generate_profit_and_loss(
            tenant=tenant,
            store=store,
            start_date=start_date,
            end_date=end_date,
            adjusted=adjusted
        )

        current_period_profit = pnl.get(
            "net_profit",
            Decimal("0.00")
        )

        total_equity += current_period_profit

        total_liabilities_and_equity = (
            total_liabilities + total_equity
        )

        difference = total_assets - total_liabilities_and_equity

        balanced = abs(difference) < Decimal("0.01")

        return {
            "tenant": tenant.id,
            "store": store.id if store else None,
        "report_type": "CONSOLIDATED" if is_consolidated else "BRANCH",
        "period": {
            "start_date": start_date,
            "end_date": end_date,
        },

        "assets": {
            "items": assets,
            "total": total_assets,
        },

        "liabilities": {
            "items": liabilities,
            "total": total_liabilities,
        },

        "equity": {
            "items": equity,
            "retained_earnings": retained_earnings,
            "current_period_profit_loss": current_period_profit,
            "total": total_equity,
        },

        "summary": {
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "total_equity": total_equity,
            "total_liabilities_and_equity": total_liabilities_and_equity,
            "difference": difference,
            "balanced": balanced,
        }
    }