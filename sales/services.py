from decimal import Decimal

from sales.models import Sale

from taxation.models import VATLedger

from ledger.models import (
    JournalEntry,
    JournalLine,
    Account
)

from inventory.models import (
    Inventory,
    InventoryMovement
)


def process_sale_posting(sale_id):

    sale = Sale.objects.get(id=sale_id)
    store=getattr(sale, "store", None)
    subtotal = Decimal('0.00')
    vat_total = Decimal('0.00')
    total_cogs = Decimal('0.00')

    # -----------------------------------
    # PROCESS ITEMS
    # -----------------------------------

    for item in sale.items.all():

        subtotal += item.subtotal
        vat_total += item.tax_amount

        inventory = Inventory.objects.filter(
            product=item.product
        ).first()

        if not inventory:
            raise ValueError(
                f"No inventory for {item.product.name}"
            )

        # -----------------------------------
        # DEDUCT STOCK
        # -----------------------------------

        inventory.deduct_quantity(
            item.quantity
        )

        # -----------------------------------
        # CALCULATE COGS
        # -----------------------------------

        unit_cost = (
            item.product.average_cost
        )

        cogs = (
            Decimal(item.quantity)
            * Decimal(unit_cost)
        )

        total_cogs += cogs

        # -----------------------------------
        # INVENTORY MOVEMENT
        # -----------------------------------

        InventoryMovement.objects.create(
            business_name=sale.organization,
            warehouse=inventory.warehouse,
            product=item.product,
            product_variant=item.product_variant,
            movement_type='SALE',
            quantity=item.quantity,
            unit_cost=unit_cost,
            total_cost=cogs,
            sale=sale,
            reference=sale.invoice_number
        )

        # -----------------------------------
        # VAT LEDGER
        # -----------------------------------

        if item.tax_amount > 0:

            VATLedger.objects.create(
                organization=sale.organization,
                vat_type='OUTPUT',
                transaction_reference=(
                    sale.invoice_number
                ),
                taxable_amount=item.subtotal,
                vat_rate=item.tax_rate_snapshot,
                vat_amount=item.tax_amount,
                reporting_period=(
                    sale.created_at.strftime('%Y-%m')
                )
            )

    # -----------------------------------
    # UPDATE SALE TOTALS
    # -----------------------------------

    sale.subtotal = subtotal
    sale.vat_total = vat_total
    sale.grand_total = subtotal + vat_total

    sale.save()

    # -----------------------------------
    # ACCOUNTS
    # -----------------------------------

    cash_account = Account.objects.get(
        code='1000'
    )

    sales_account = Account.objects.get(
        code='4000'
    )

    vat_account = Account.objects.get(
        code='2000'
    )

    cogs_account = Account.objects.get(
        code='5000'
    )

    inventory_account = Account.objects.get(
        code='1200'
    )

    entry = JournalEntry.objects.create(
        organization=sale.organization,
        reference=f'SALE-{sale.invoice_number}',
        description='Sales Transaction',
        entry_date=sale.created_at.date(),
        status='POSTED',
        created_by=sale.cashier
    )

    # DR CASH

    JournalLine.objects.create(
        journal_entry=entry,
        store=store,
        account=cash_account,
        description='Cash Received',
        debit=sale.grand_total,
        credit=0
    )

    # CR SALES

    JournalLine.objects.create(
        journal_entry=entry,
        store=store,
        account=sales_account,
        description='Sales Revenue',
        debit=0,
        credit=sale.subtotal
    )

    # CR VAT

    if sale.vat_total > 0:

        JournalLine.objects.create(
            journal_entry=entry,
            store=store,
            account=vat_account,
            description='VAT Payable',
            debit=0,
            credit=sale.vat_total
        )

    # DR COGS

    JournalLine.objects.create(
        journal_entry=entry,
        store=store,
        account=cogs_account,
        description='Cost Of Goods Sold',
        debit=total_cogs,
        credit=0
    )

    # CR INVENTORY

    JournalLine.objects.create(
        journal_entry=entry,
        store=store,
        account=inventory_account,
        description='Inventory Reduction',
        debit=0,
        credit=total_cogs
    )

    return entry