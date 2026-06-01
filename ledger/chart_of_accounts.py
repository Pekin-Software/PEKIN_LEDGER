from django_tenants.utils import schema_context
from ledger.models import Account


DEFAULT_ACCOUNTS = [
    # Assets
    ("1000", "Cash", "ASSET"),
    ("1010", "Bank Account", "ASSET"),
    ("1100", "Accounts Receivable", "ASSET"),
    ("1200", "Inventory", "ASSET"),
    ("1300", "VAT Receivable", "ASSET"),

    # Inter-Store Clearing
    ("1399", "Inter-Store Clearing Account", "ASSET"),

    # Liabilities
    ("2000", "Accounts Payable", "LIABILITY"),
    ("2100", "VAT Payable", "LIABILITY"),
    ("2200", "Payroll Payable", "LIABILITY"),
    ("9999", "Suspense Account", "LIABILITY"),

    # Equity
    ("3000", "Owner Equity", "EQUITY"),
    ("3100", "Retained Earnings", "EQUITY"),

    # Revenue
    ("4000", "Sales Revenue", "REVENUE"),
    ("4100", "Service Revenue", "REVENUE"),

    # Expenses
    ("5000", "Cost of Goods Sold", "EXPENSE"),
    ("5100", "Salaries Expense", "EXPENSE"),
    ("5200", "Rent Expense", "EXPENSE"),
    ("5300", "Utilities Expense", "EXPENSE"),
    ("5400", "General Expense", "EXPENSE"),
]


def seed_chart_of_accounts(client):
    """
    Create default ledger accounts inside the tenant schema.
    Safe to run multiple times.
    """

    with schema_context(client.schema_name):
        for code, name, account_type in DEFAULT_ACCOUNTS:
            Account.objects.get_or_create(
                tenant=client,
                code=code,
                defaults={
                    "name": name,
                    "account_type": account_type,
                    "is_active": True,
                }
            )