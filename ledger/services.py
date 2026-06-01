from decimal import Decimal
from .models import JournalEntry


def validate_journal_entry(entry_id):

    entry = JournalEntry.objects.get(id=entry_id)

    debit_total = Decimal('0.00')
    credit_total = Decimal('0.00')

    for line in entry.lines.all():
        debit_total += line.debit
        credit_total += line.credit

    if debit_total != credit_total:
        raise Exception('Journal Entry is not balanced')

    return True


def post_journal_entry(entry_id):

    entry = JournalEntry.objects.get(id=entry_id)

    validate_journal_entry(entry_id)

    entry.status = 'POSTED'
    entry.save()

    return entry