from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from community._cashapp_import_csv import (
    MAX_ROWS,
    parse_amount,
    parse_cashapp_csv,
    parse_cashapp_datetime,
)
from community._validation import Code, ValidationException
from django.conf import settings

from tests._cashapp_helpers import HEADER, csv_line, make_csv


class TestHeaders:
    def test_real_export_headers_parse_every_field(self):
        rows = parse_cashapp_csv(make_csv(csv_line(note="for the potluck")))
        assert len(rows) == 1
        r = rows[0]
        assert r.payment_id == "tx1"
        assert r.transaction_id == "tx1"
        assert r.amount == Decimal("15")
        assert r.status == "COMPLETE"
        assert r.transaction_type == "P2P"
        assert r.sender_name == "Alex Kim"
        assert r.note == "for the potluck"
        assert r.paid_at == datetime(2026, 10, 1, 22, 22, 11, tzinfo=UTC)

    def test_headers_match_case_insensitively_with_padding(self):
        text = "  DATE ,AMOUNT, status ,NAME OF SENDER/RECEIVER\n2026-10-01 18:00:00,$15,complete,Alex\n"
        r = parse_cashapp_csv(text)[0]
        assert (r.amount, r.status, r.sender_name) == (Decimal("15"), "COMPLETE", "Alex")

    def test_missing_optional_columns_default_to_blank_and_row_index_id(self):
        text = "Date,Amount,Status,Name\n2026-10-01 18:00:00,$15,COMPLETE,Alex\n"
        r = parse_cashapp_csv(text)[0]
        assert r.transaction_id == ""
        assert r.payment_id == "row-0"
        assert r.note == ""
        assert r.transaction_type == ""

    def test_net_amount_used_when_amount_column_absent(self):
        text = "Date,Net Amount,Status,Name\n2026-10-01 18:00:00,$14.50,COMPLETE,Alex\n"
        assert parse_cashapp_csv(text)[0].amount == Decimal("14.50")

    def test_bom_is_stripped(self):
        rows = parse_cashapp_csv("﻿" + make_csv(csv_line()))
        assert rows[0].payment_id == "tx1"

    def test_missing_required_columns_names_them(self):
        with pytest.raises(ValidationException) as exc:
            parse_cashapp_csv("Transaction ID,Notes\nabc,hi\n")
        assert exc.value.code == Code.CashAppImport.CSV_MISSING_COLUMNS
        assert exc.value.params == {"columns": "amount, date, name, status"}
        assert exc.value.status_code == 400

    def test_empty_text_raises_empty(self):
        with pytest.raises(ValidationException) as exc:
            parse_cashapp_csv("")
        assert exc.value.code == Code.CashAppImport.CSV_EMPTY

    def test_header_only_raises_empty(self):
        with pytest.raises(ValidationException) as exc:
            parse_cashapp_csv(HEADER + "\n\n")
        assert exc.value.code == Code.CashAppImport.CSV_EMPTY

    def test_blank_rows_are_skipped_and_ids_stay_dense(self):
        text = make_csv(csv_line(tx=""), ",,,,,,,,,,,,,", csv_line(tx=""))
        assert [r.payment_id for r in parse_cashapp_csv(text)] == ["row-0", "row-1"]

    def test_quoted_note_with_commas(self):
        text = make_csv(csv_line(note='"for alex, sam, and jo"'))
        assert parse_cashapp_csv(text)[0].note == "for alex, sam, and jo"

    def test_a_few_thousand_rows_parse(self):
        lines = [csv_line(tx=f"tx{i}") for i in range(3000)]
        assert len(parse_cashapp_csv(make_csv(*lines))) == 3000

    def test_too_many_rows_raises(self):
        lines = [csv_line(tx=f"tx{i}") for i in range(MAX_ROWS + 1)]
        with pytest.raises(ValidationException) as exc:
            parse_cashapp_csv(make_csv(*lines))
        assert exc.value.code == Code.CashAppImport.CSV_TOO_MANY_ROWS
        assert exc.value.params == {"max_rows": MAX_ROWS}


class TestStatus:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("COMPLETE", "COMPLETE"),
            ("complete", "COMPLETE"),
            ("PAYMENT_DEPOSITED", "PAYMENT_DEPOSITED"),
            ("Payment Deposited", "PAYMENT_DEPOSITED"),
            ("PAYMENT_SENT", "PAYMENT_SENT"),
            ("CANCELED", "CANCELED"),
            ("FAILED", "FAILED"),
            ("REFUNDED", "REFUNDED"),
        ],
    )
    def test_status_is_normalized(self, raw, expected):
        assert parse_cashapp_csv(make_csv(csv_line(status=raw)))[0].status == expected


class TestAmount:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("$15", Decimal("15")),
            ("15", Decimal("15")),
            ("$15.00", Decimal("15.00")),
            ("-$15", Decimal("-15")),
            ("$-15", Decimal("-15")),
            ("($15.00)", Decimal("-15.00")),
            ("$1,200.00", Decimal("1200.00")),
            (" $ 7.5 ", Decimal("7.5")),
            ("+$15.00", Decimal("15.00")),
            ("$+15", Decimal("15")),
        ],
    )
    def test_money_formats(self, raw, expected):
        assert parse_amount(raw) == expected

    @pytest.mark.parametrize("raw", ["", "abc", "$", "15 dollars"])
    def test_unreadable_amount_is_none(self, raw):
        assert parse_amount(raw) is None

    def test_raw_amount_and_date_are_kept_for_review(self):
        r = parse_cashapp_csv(make_csv(csv_line(amount="fifteen", date="someday")))[0]
        assert (r.amount, r.paid_at) == (None, None)
        assert (r.raw_amount, r.raw_date) == ("fifteen", "someday")

    def test_quoted_thousands_amount_in_csv(self):
        text = make_csv(csv_line(amount='"$1,200.00"'))
        assert parse_cashapp_csv(text)[0].amount == Decimal("1200.00")


class TestDates:
    @pytest.mark.parametrize(
        ("raw", "utc_hour"),
        [
            ("2026-10-01 18:22:11 EDT", 22),
            ("2026-10-01 18:22:11 EST", 23),
            ("2026-10-01 18:22:11 PDT", 1),
            ("2026-10-01 18:22:11 UTC", 18),
            ("2026-10-01 18:22:11 -0400", 22),
            ("2026-10-01 18:22:11 +01:00", 17),
            ("2026-10-01T18:22:11Z", 18),
            ("2026-10-01T18:22:11-04:00", 22),
        ],
    )
    def test_timezones(self, raw, utc_hour):
        assert parse_cashapp_datetime(raw).astimezone(UTC).hour == utc_hour

    def test_no_zone_assumes_new_york(self):
        parsed = parse_cashapp_datetime("2026-10-01 18:22:11")
        assert parsed.tzinfo == settings.COMMUNITY_TZ
        assert parsed.utcoffset() == timedelta(hours=-4)

    def test_no_zone_in_winter_uses_eastern_standard(self):
        parsed = parse_cashapp_datetime("2026-12-01 18:22:11")
        assert parsed.utcoffset() == timedelta(hours=-5)

    def test_us_slash_format(self):
        parsed = parse_cashapp_datetime("10/01/2026 18:22:11 EDT")
        assert parsed == datetime(2026, 10, 1, 18, 22, 11, tzinfo=timezone(timedelta(hours=-4)))

    @pytest.mark.parametrize("raw", ["", "yesterday", "2026-13-01 10:00:00 EDT"])
    def test_unreadable_dates_are_none(self, raw):
        assert parse_cashapp_datetime(raw) is None
