from decimal import Decimal

from ledger.models import Account, JournalEntry, JournalLine


class InterStoreTransferService:

    @staticmethod
    def create_inventory_transfer_journal(transfer, inventory_value):
        inventory_value = Decimal(inventory_value)

        if inventory_value <= Decimal("0.00"):
            raise ValueError("Inventory transfer value must be greater than zero.")

        if transfer.source_store_id == transfer.destination_store_id:
            raise ValueError("Source store and destination store cannot be the same.")

        inventory_account = Account.objects.get(
            tenant=transfer.tenant,
            code="1200"
        )

        inter_store_account = Account.objects.get(
            tenant=transfer.tenant,
            code="1399"
        )

        source_entry = JournalEntry.objects.create(
            tenant=transfer.tenant,
            store=transfer.source_store,
            is_inter_store=True,
            source_store=transfer.source_store,
            destination_store=transfer.destination_store,
            reference=f"TRF-OUT-{transfer.id}",
            description=(
                f"Inventory Transfer OUT from "
                f"{transfer.source_store.store_name} to "
                f"{transfer.destination_store.store_name}"
            ),
            entry_date=transfer.created_at.date(),
            status="POSTED"
        )

        JournalLine.objects.create(
            journal_entry=source_entry,
            store=transfer.source_store,
            account=inter_store_account,
            description="Inter-Store Transfer Clearing",
            debit=inventory_value,
            credit=Decimal("0.00")
        )

        JournalLine.objects.create(
            journal_entry=source_entry,
            store=transfer.source_store,
            account=inventory_account,
            description="Inventory Reduction",
            debit=Decimal("0.00"),
            credit=inventory_value
        )

        destination_entry = JournalEntry.objects.create(
            tenant=transfer.tenant,
            store=transfer.destination_store,
            is_inter_store=True,
            source_store=transfer.source_store,
            destination_store=transfer.destination_store,
            reference=f"TRF-IN-{transfer.id}",
            description=(
                f"Inventory Transfer IN from "
                f"{transfer.source_store.store_name} to "
                f"{transfer.destination_store.store_name}"
            ),
            entry_date=transfer.created_at.date(),
            status="POSTED"
        )

        JournalLine.objects.create(
            journal_entry=destination_entry,
            store=transfer.destination_store,
            account=inventory_account,
            description="Inventory Increase",
            debit=inventory_value,
            credit=Decimal("0.00")
        )

        JournalLine.objects.create(
            journal_entry=destination_entry,
            store=transfer.destination_store,
            account=inter_store_account,
            description="Inter-Store Transfer Clearing",
            debit=Decimal("0.00"),
            credit=inventory_value
        )

        return {
            "source_entry_id": source_entry.id,
            "destination_entry_id": destination_entry.id
        }