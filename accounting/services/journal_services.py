from ledger.models import Account, JournalEntry, JournalLine


class JournalService:

    @staticmethod
    def create_purchase_journal(purchase):
        store = getattr(purchase, "store", None)

        inventory_account = Account.objects.get(
            tenant=purchase.tenant,
            code='1200'
        )

        vat_receivable = Account.objects.get(
            tenant=purchase.tenant,
            code='1300'
        )

        accounts_payable = Account.objects.get(
            tenant=purchase.tenant,
            code='2000'
        )

        entry = JournalEntry.objects.create(
            tenant=purchase.tenant,
            store=getattr(purchase, "store", None),
            reference=f'PUR-{purchase.invoice_number}',
            description='Inventory Purchase',
            entry_date=purchase.created_at.date(),
            status='POSTED'
        )

        JournalLine.objects.create(
            journal_entry=entry,
            store=store,
            account=inventory_account,
            description='Inventory Asset',
            debit=purchase.subtotal,
            credit=0
        )

        if purchase.vat_total > 0:
            JournalLine.objects.create(
                journal_entry=entry,
                store=store,
                account=vat_receivable,
                description='Input VAT',
                debit=purchase.vat_total,
                credit=0
            )

        JournalLine.objects.create(
            journal_entry=entry,
            store=store,
            account=accounts_payable,
            description='Supplier Liability',
            debit=0,
            credit=purchase.grand_total
        )

        return entry.id

    @staticmethod
    def create_sales_journal(sale):
        store = getattr(sale, "store", None)
        cash_account = Account.objects.get(
            tenant=sale.tenant,
            code='1000'
        )

        sales_account = Account.objects.get(
            tenant=sale.tenant,
            code='4000'
        )

        vat_account = Account.objects.get(
            tenant=sale.tenant,
            code='2100'
        )

        entry = JournalEntry.objects.create(
            tenant=sale.tenant,
            store=getattr(sale, "store", None),
            reference=f'SALE-{sale.invoice_number}',
            description='Sales Transaction',
            entry_date=sale.created_at.date(),
            status='POSTED'
        )

        JournalLine.objects.create(
            journal_entry=entry,
            store=store,
            account=cash_account,
            description='Cash Received',
            debit=sale.grand_total,
            credit=0
        )

        JournalLine.objects.create(
            journal_entry=entry,
            store=store,
            account=sales_account,
            description='Sales Revenue',
            debit=0,
            credit=sale.subtotal
        )

        if sale.vat_total > 0:
            JournalLine.objects.create(
                journal_entry=entry,
                store=store,
                account=vat_account,
                description='Output VAT',
                debit=0,
                credit=sale.vat_total
            )

        return entry.id

    @staticmethod
    def create_cogs_journal(sale, cogs_amount):
        store = getattr(sale, "store", None)
        inventory_account = Account.objects.get(
            tenant=sale.tenant,
            code='1200'
        )

        cogs_account = Account.objects.get(
            tenant=sale.tenant,
            code='5000'
        )

        entry = JournalEntry.objects.create(
            tenant=sale.tenant,
            store=getattr(sale, "store", None),
            reference=f'COGS-{sale.id}',
            description='Cost Of Goods Sold',
            entry_date=sale.created_at.date(),
            status='POSTED'
        )

        JournalLine.objects.create(
            journal_entry=entry,
            store=store,
            account=cogs_account,
            description='COGS Expense',
            debit=cogs_amount,
            credit=0
        )

        JournalLine.objects.create(
            journal_entry=entry,
            store=store,
            account=inventory_account,
            description='Inventory Reduction',
            debit=0,
            credit=cogs_amount
        )

        return entry.id