import csv
import io
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from django.conf import settings

from community._validation import Code, raise_validation

MAX_ROWS = 10_000

_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "transaction_id": ("transaction id", "id"),
    "date": ("date", "transaction date", "date/time"),
    "transaction_type": ("transaction type", "type"),
    "amount": ("amount", "net amount"),
    "status": ("status", "transaction status"),
    "note": ("notes", "note", "memo"),
    "name": ("name of sender/receiver", "name", "sender", "counterparty"),
}
_REQUIRED = ("amount", "date", "name", "status")

_TZ_OFFSETS_HOURS = {
    "UTC": 0,
    "GMT": 0,
    "Z": 0,
    "EDT": -4,
    "EST": -5,
    "CDT": -5,
    "CST": -6,
    "MDT": -6,
    "MST": -7,
    "PDT": -7,
    "PST": -8,
}
_OFFSET_RE = re.compile(r"^([+-])(\d{2}):?(\d{2})$")
_AMOUNT_RE = re.compile(r"^([+-])?\$?([+-])?([\d,]*\.?\d+)$")
_FALLBACK_DATE_FORMATS = ("%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M", "%m/%d/%Y")


@dataclass(frozen=True)
class CashAppRow:
    """param(amount): signed; None when unreadable. param(paid_at): aware; None when unreadable."""

    payment_id: str
    row_index: int
    transaction_id: str
    paid_at: datetime | None
    amount: Decimal | None
    status: str
    transaction_type: str
    sender_name: str
    note: str
    raw_amount: str = ""
    raw_date: str = ""


def parse_amount(raw: str) -> Decimal | None:
    text = raw.strip().replace(" ", "")
    negative_parens = text.startswith("(") and text.endswith(")")
    if negative_parens:
        text = text[1:-1]
    match = _AMOUNT_RE.match(text)
    if not match:
        return None
    sign_a, sign_b, digits = match.groups()
    try:
        value = Decimal(digits.replace(",", ""))
    except InvalidOperation:
        return None
    return -value if "-" in (sign_a, sign_b) or negative_parens else value


def _tzinfo_for(token: str) -> timezone | None:
    upper = token.upper()
    if upper in _TZ_OFFSETS_HOURS:
        return timezone(timedelta(hours=_TZ_OFFSETS_HOURS[upper]))
    match = _OFFSET_RE.match(token)
    if not match:
        return None
    sign, hours, minutes = match.groups()
    delta = timedelta(hours=int(hours), minutes=int(minutes))
    return timezone(-delta if sign == "-" else delta)


def _parse_naive(text: str) -> datetime | None:
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        pass
    for fmt in _FALLBACK_DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _split_tz(text: str) -> tuple[str, timezone | None]:
    head, _, tail = text.rpartition(" ")
    tz = _tzinfo_for(tail) if head else None
    if tz is not None:
        return head, tz
    if text.endswith("Z"):
        return text[:-1], UTC
    return text, None


def parse_cashapp_datetime(raw: str) -> datetime | None:
    """Naive timestamps are read in the community timezone."""
    base, tz = _split_tz(raw.strip())
    parsed = _parse_naive(base)
    if parsed is None:
        return None
    if parsed.tzinfo is not None:
        return parsed
    return parsed.replace(tzinfo=tz or settings.COMMUNITY_TZ)


def _normalize_status(raw: str) -> str:
    return "_".join(raw.strip().upper().split())


def _resolve_columns(fieldnames: list[str]) -> dict[str, str]:
    present = {(h or "").strip().lower(): h for h in fieldnames}
    resolved: dict[str, str] = {}
    for key, aliases in _COLUMN_ALIASES.items():
        header = next((present[a] for a in aliases if a in present), None)
        if header is not None:
            resolved[key] = header
    missing = [key for key in _REQUIRED if key not in resolved]
    if missing:
        raise_validation(
            Code.CashAppImport.CSV_MISSING_COLUMNS, status_code=400, columns=", ".join(missing)
        )
    return resolved


def _row_to_payment(index: int, raw: dict[str, str | None], columns: dict[str, str]) -> CashAppRow:
    def cell(key: str) -> str:
        header = columns.get(key)
        return (raw.get(header) or "").strip() if header else ""

    transaction_id = cell("transaction_id")
    raw_amount, raw_date = cell("amount"), cell("date")
    return CashAppRow(
        payment_id=transaction_id or f"row-{index}",
        row_index=index,
        transaction_id=transaction_id,
        paid_at=parse_cashapp_datetime(raw_date),
        amount=parse_amount(raw_amount),
        status=_normalize_status(cell("status")),
        transaction_type=cell("transaction_type"),
        sender_name=cell("name"),
        note=cell("note"),
        raw_amount=raw_amount,
        raw_date=raw_date,
    )


def _is_blank(raw: dict[str, str | None]) -> bool:
    return not any((v or "").strip() for v in raw.values() if isinstance(v, str))


def parse_cashapp_csv(text: str) -> list[CashAppRow]:
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    if not reader.fieldnames:
        raise_validation(Code.CashAppImport.CSV_EMPTY, status_code=400)
    columns = _resolve_columns(list(reader.fieldnames))

    rows: list[CashAppRow] = []
    for raw in reader:
        if _is_blank(raw):
            continue
        if len(rows) >= MAX_ROWS:
            raise_validation(
                Code.CashAppImport.CSV_TOO_MANY_ROWS, status_code=400, max_rows=MAX_ROWS
            )
        rows.append(_row_to_payment(len(rows), raw, columns))
    if not rows:
        raise_validation(Code.CashAppImport.CSV_EMPTY, status_code=400)
    return rows
