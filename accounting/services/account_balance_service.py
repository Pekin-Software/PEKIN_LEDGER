from django.db.models import Sum
from django.db.models.functions import Coalesce
from decimal import Decimal
from ledger.models import JournalLine


class AccountBalanceService:

    @staticmethod
    def get_account_balance(
        account,
        tenant,
        store=None,
        start_date=None,
        end_date=None,
        adjusted=True,
        exclude_inter_store=False
    ):

        lines = JournalLine.objects.filter(
            account=account,
            account__tenant=tenant,
            journal_entry__tenant=tenant
        )

        if store is not None:
            lines = lines.filter(
                store=store
            )

        if start_date:
            lines = lines.filter(
                journal_entry__entry_date__gte=start_date
            )

        if end_date:
            lines = lines.filter(
                journal_entry__entry_date__lte=end_date
            )

        if adjusted:
            lines = lines.filter(
                journal_entry__status="POSTED"
            )

        if exclude_inter_store:
            lines = lines.filter(
                journal_entry__is_inter_store=False
            )

        totals = lines.aggregate(
            debit_total=Coalesce(
                Sum("debit"),
                Decimal("0.00")
            ),
            credit_total=Coalesce(
                Sum("credit"),
                Decimal("0.00")
            )
        )

        debit_total = totals["debit_total"]
        credit_total = totals["credit_total"]

        if account.account_type in ["ASSET", "EXPENSE"]:
            return debit_total - credit_total

        return credit_total - debit_total