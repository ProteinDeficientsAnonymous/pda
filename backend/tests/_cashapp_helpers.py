from datetime import UTC, datetime
from decimal import Decimal

from community._cashapp_import_csv import CashAppRow
from community._cashapp_import_types import EventPaymentContext

HEADER = (
    "Transaction ID,Date,Transaction Type,Currency,Amount,Fee,Net Amount,Asset Type,"
    "Asset Price,Asset Amount,Status,Notes,Name of sender/receiver,Account"
)
CREATED = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
ENDS = datetime(2026, 10, 5, 2, 0, tzinfo=UTC)
IN_WINDOW = datetime(2026, 10, 1, 22, 0, tzinfo=UTC)


_CSV_DEFAULTS = {
    "tx": "tx1",
    "date": "2026-10-01 18:22:11 EDT",
    "tx_type": "P2P",
    "amount": "$15",
    "status": "COMPLETE",
    "note": "",
    "name": "Alex Kim",
}


def csv_line(**fields: str) -> str:
    f = {**_CSV_DEFAULTS, **fields}
    return (
        f"{f['tx']},{f['date']},{f['tx_type']},USD,{f['amount']},$0,{f['amount']},,,,"
        f"{f['status']},{f['note']},{f['name']},Visa Debit 1234"
    )


def make_csv(*lines: str, header: str = HEADER) -> str:
    return "\n".join([header, *lines]) + "\n"


def event_ctx(price="$15", ends_at=ENDS, is_paid_event=True) -> EventPaymentContext:
    return EventPaymentContext(
        created_at=CREATED, ends_at=ends_at, price=price, is_paid_event=is_paid_event
    )


def row(index: int = 0, amount: str | None = "15", **overrides) -> CashAppRow:
    tx = overrides.pop("tx", "")
    fields = {
        "paid_at": IN_WINDOW,
        "status": "COMPLETE",
        "transaction_type": overrides.pop("tx_type", "P2P"),
        "sender_name": overrides.pop("sender", "Alex Kim"),
        "note": "",
        **overrides,
    }
    return CashAppRow(
        payment_id=tx or f"row-{index}",
        row_index=index,
        transaction_id=tx,
        amount=Decimal(amount) if amount is not None else None,
        **fields,
    )
