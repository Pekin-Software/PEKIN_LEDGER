from ledger.models import JournalEntry


class GeneralLedgerService:

    @staticmethod
    def generate_general_ledger(
        tenant,
        store=None,
        start_date=None,
        end_date=None
    ):

        queryset = (
            JournalEntry.objects.filter(
                tenant=tenant,
                status='POSTED'
            )
            .select_related('tenant', 'store')
            .prefetch_related('lines__account')
            .order_by('entry_date', 'id')
        )

        if store:
            queryset = queryset.filter(
                lines__store=store
            ).distinct()

        if start_date:
            queryset = queryset.filter(entry_date__gte=start_date)

        if end_date:
            queryset = queryset.filter(entry_date__lte=end_date)

        report = []

        for entry in queryset:

            lines = []

            for line in entry.lines.all():

                if store and line.store_id != store.id:
                    continue
                lines.append({
                    'store': line.store.name if line.store else None,
                    'account_code': line.account.code,
                    'account': line.account.name,
                    'account_type': line.account.account_type,
                    'debit': line.debit,
                    'credit': line.credit,
                    'description': line.description,
                    'is_reconciled': line.is_reconciled,
                    'reconciliation_reference': line.reconciliation_reference,
                })

            report.append({
                'tenant': entry.tenant.business_name if entry.tenant else None,
                'store': entry.store.name if entry.store else None,
                'reference': entry.reference,
                'description': entry.description,
                'entry_date': entry.entry_date,
                'cash_flow_category': entry.cash_flow_category,
                'is_reconciled': entry.is_reconciled,
                'reconciliation_reference': entry.reconciliation_reference,
                'is_inter_store': entry.is_inter_store,
                'source_store': entry.source_store.name if entry.source_store else None,
                'destination_store': entry.destination_store.name if entry.destination_store else None,
                'lines': lines
            })

        return report