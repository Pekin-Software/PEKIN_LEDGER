from decimal import Decimal

from ledger.models import Account
from stores.models import Store

from accounting.services.account_balance_service import AccountBalanceService


class TrialBalanceService:

    INTER_STORE_CLEARING_CODES = [
        "1399",
    ]

    @staticmethod
    def generate_trial_balance(
        tenant,
        store=None,
        start_date=None,
        end_date=None,
        adjusted=True
    ):

        accounts = Account.objects.filter(
            tenant=tenant,
            is_active=True
        ).order_by("code")

        report = []

        total_debits = Decimal("0.00")
        total_credits = Decimal("0.00")

        for account in accounts:

            balance = AccountBalanceService.get_account_balance(
                account=account,
                tenant=tenant,
                store=store,
                start_date=start_date,
                end_date=end_date,
                adjusted=adjusted,
                exclude_inter_store=False,
            )

            if balance == 0:
                continue

            debit = Decimal("0.00")
            credit = Decimal("0.00")

            if balance > 0:
                if account.account_type in ["ASSET", "EXPENSE"]:
                    debit = balance
                else:
                    credit = balance
            else:
                if account.account_type in ["ASSET", "EXPENSE"]:
                    credit = abs(balance)
                else:
                    debit = abs(balance)

            total_debits += debit
            total_credits += credit

            report.append({
                "branch_code": store.branch_code if store else None,
                "store_name": store.store_name if store else None,
                "account_code": account.code,
                "account_name": account.name,
                "account_type": account.account_type,
                "debit": debit,
                "credit": credit,
            })

        return {
            "report_type": "ADJUSTED_TRIAL_BALANCE" if adjusted else "UNADJUSTED_TRIAL_BALANCE",
            "scope": "STORE" if store else "BUSINESS",
            "tenant": {
                "id": tenant.id,
                "business_name": tenant.business_name,
                "schema_name": tenant.schema_name,
            },
            "store": {
                "id": store.id,
                "store_name": store.store_name,
                "branch_code": store.branch_code,
            } if store else None,
            "accounts": report,
            "total_debits": total_debits,
            "total_credits": total_credits,
            "balanced": total_debits == total_credits,
        }

    @staticmethod
    def generate_master_trial_balance(
        tenant,
        start_date=None,
        end_date=None
    ):

        accounts = Account.objects.filter(
            tenant=tenant,
            is_active=True
        ).order_by("code")

        stores = Store.objects.filter(
            tenant=tenant
        ).order_by("branch_code")

        report = []

        total_debits = Decimal("0.00")
        total_credits = Decimal("0.00")

        for account in accounts:

            balance = AccountBalanceService.get_account_balance(
                account=account,
                tenant=tenant,
                store=None,
                start_date=start_date,
                end_date=end_date,
                adjusted=True,
                exclude_inter_store=True,
            )

            if account.code in TrialBalanceService.INTER_STORE_CLEARING_CODES:
                continue

            if balance == 0:
                continue

            debit = Decimal("0.00")
            credit = Decimal("0.00")

            if balance > 0:
                if account.account_type in ["ASSET", "EXPENSE"]:
                    debit = balance
                else:
                    credit = balance
            else:
                if account.account_type in ["ASSET", "EXPENSE"]:
                    credit = abs(balance)
                else:
                    debit = abs(balance)

            total_debits += debit
            total_credits += credit

            report.append({
                "account_code": account.code,
                "account_name": account.name,
                "account_type": account.account_type,
                "debit": debit,
                "credit": credit,
            })

        branch_summaries = []

        for store in stores:
            branch_tb = TrialBalanceService.generate_trial_balance(
                tenant=tenant,
                store=store,
                start_date=start_date,
                end_date=end_date,
                adjusted=True,
            )

            branch_summaries.append({
                "store_id": store.id,
                "store_name": store.store_name,
                "branch_code": store.branch_code,
                "total_debits": branch_tb["total_debits"],
                "total_credits": branch_tb["total_credits"],
                "balanced": branch_tb["balanced"],
            })

        return {
            "report_type": "MASTER_CONSOLIDATED_TRIAL_BALANCE",
            "tenant": {
                "id": tenant.id,
                "business_name": tenant.business_name,
                "schema_name": tenant.schema_name,
            },
            "consolidation_note": "Inter-store clearing transactions have been eliminated.",
            "branches": branch_summaries,
            "accounts": report,
            "total_debits": total_debits,
            "total_credits": total_credits,
            "balanced": total_debits == total_credits,
        }