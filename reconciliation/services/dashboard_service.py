from ..models import (
    CashTransaction,
    CashReconciliation,
    MobileMoneyTransaction,
    MobileMoneyReconciliation,
    SupplierVATTransaction,
    SupplierVATReconciliation,
    ReconciliationException
)


class ReconciliationDashboardService:

    @staticmethod
    def generate_dashboard(
        tenant,
        store=None,
    ):
        cash_txn_qs = CashTransaction.objects.filter(
            tenant=tenant
        )

        cash_rec_qs = CashReconciliation.objects.filter(
            tenant=tenant
        )

        momo_txn_qs = MobileMoneyTransaction.objects.filter(
            tenant=tenant
        )

        momo_rec_qs = MobileMoneyReconciliation.objects.filter(
            tenant=tenant
        )

        supplier_vat_txn_qs = SupplierVATTransaction.objects.filter(
            tenant=tenant
        )

        supplier_vat_rec_qs = SupplierVATReconciliation.objects.filter(
            tenant=tenant
        )

        exception_qs = ReconciliationException.objects.filter(
            tenant=tenant
        )

        if store:
            cash_txn_qs = cash_txn_qs.filter(store=store)
            cash_rec_qs = cash_rec_qs.filter(store=store)
            momo_txn_qs = momo_txn_qs.filter(store=store)
            momo_rec_qs = momo_rec_qs.filter(store=store)
            supplier_vat_txn_qs = supplier_vat_txn_qs.filter(store=store)
            supplier_vat_rec_qs = supplier_vat_rec_qs.filter(store=store)
            exception_qs = exception_qs.filter(store=store)

        return {
            "cash_transactions": cash_txn_qs.count(),
            "unreconciled_cash_transactions": cash_txn_qs.filter(
                is_reconciled=False
            ).count(),
            "cash_reconciliations": cash_rec_qs.count(),
            "cash_shortages": cash_rec_qs.filter(
                status="SHORTAGE"
            ).count(),
            "cash_overages": cash_rec_qs.filter(
                status="OVERAGE"
            ).count(),

            "mobile_money_transactions": momo_txn_qs.count(),
            "unreconciled_mobile_money_transactions": momo_txn_qs.filter(
                is_reconciled=False
            ).count(),
            "mobile_money_reconciliations": momo_rec_qs.count(),
            "mobile_money_mismatches": momo_rec_qs.filter(
                status="MISMATCH"
            ).count(),

            "supplier_vat_transactions": supplier_vat_txn_qs.count(),
            "unreconciled_supplier_vat_transactions": supplier_vat_txn_qs.filter(
                is_reconciled=False
            ).count(),
            "supplier_vat_reconciliations": supplier_vat_rec_qs.count(),
            "supplier_vat_mismatches": supplier_vat_rec_qs.filter(
                status="MISMATCH"
            ).count(),

            "open_exceptions": exception_qs.filter(
                resolved=False
            ).count(),
        }