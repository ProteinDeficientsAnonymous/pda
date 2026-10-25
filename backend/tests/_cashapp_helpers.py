HEADER = (
    "Transaction ID,Date,Transaction Type,Currency,Amount,Fee,Net Amount,Asset Type,"
    "Asset Price,Asset Amount,Status,Notes,Name of sender/receiver,Account"
)


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
