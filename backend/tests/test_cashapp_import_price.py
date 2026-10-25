from decimal import Decimal

import pytest
from community._cashapp_import_price import (
    PeopleRange,
    PriceKind,
    PriceSpec,
    parse_event_price,
    people_for_amount,
)

D = Decimal


class TestParseEventPrice:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("$15", PriceSpec(PriceKind.EXACT, D("15"), D("15"))),
            ("15", PriceSpec(PriceKind.EXACT, D("15"), D("15"))),
            ("$12.50", PriceSpec(PriceKind.EXACT, D("12.50"), D("12.50"))),
            ("$15 at the door", PriceSpec(PriceKind.EXACT, D("15"), D("15"))),
            ("$1,000", PriceSpec(PriceKind.EXACT, D("1000"), D("1000"))),
            ("$10–20 sliding scale", PriceSpec(PriceKind.RANGE, D("10"), D("20"))),
            ("$10-$20", PriceSpec(PriceKind.RANGE, D("10"), D("20"))),
            ("$20 - $10", PriceSpec(PriceKind.RANGE, D("10"), D("20"))),
            ("10 to 20", PriceSpec(PriceKind.RANGE, D("10"), D("20"))),
            ("$10+", PriceSpec(PriceKind.RANGE, D("10"), None)),
            ("$10 or more", PriceSpec(PriceKind.RANGE, D("10"), None)),
            ("2 for $25", PriceSpec(PriceKind.EXACT, D("25"), D("25"))),
            ("$15 (doors at 7)", PriceSpec(PriceKind.EXACT, D("15"), D("15"))),
            ("doors at 7, $10-15", PriceSpec(PriceKind.RANGE, D("10"), D("15"))),
            ("$10/20", PriceSpec(PriceKind.RANGE, D("10"), D("20"))),
            ("$10-20", PriceSpec(PriceKind.RANGE, D("10"), D("20"))),
            ("$15 / $20 at door", PriceSpec(PriceKind.RANGE, D("15"), D("20"))),
            ("$15 or $20", PriceSpec(PriceKind.RANGE, D("15"), D("20"))),
            ("$10-$20+", PriceSpec(PriceKind.RANGE, D("10"), None)),
            ("$10 - 20 or more", PriceSpec(PriceKind.RANGE, D("10"), None)),
        ],
    )
    def test_readable_prices(self, raw, expected):
        assert parse_event_price(raw) == expected

    @pytest.mark.parametrize(
        "raw",
        [
            "",
            "   ",
            "free",
            "FREE!",
            "pay what you can",
            "pwyc",
            "suggested donation $15",
            "$0",
            "$5 / $10 / $15",
            "bring a dish",
            "$15 + $3 fee",
            "$25 ($5 off for members)",
            "$20 includes $5 drink",
            "$15 tip $5",
            "doors at 7, 15 dollars",
            "$15 ($20 with a plus one)",
        ],
    )
    def test_unparseable_prices(self, raw):
        assert parse_event_price(raw).kind == PriceKind.UNPARSEABLE

    def test_comma_between_two_small_numbers_is_a_range_not_thousands(self):
        assert parse_event_price("$10,20") == PriceSpec(PriceKind.RANGE, D("10"), D("20"))

    def test_bare_numbers_are_ignored_once_a_dollar_amount_exists(self):
        assert parse_event_price("$12 for 1-2 hours") == PriceSpec(
            PriceKind.EXACT, D("12"), D("12")
        )


class TestPeopleForAmount:
    exact = PriceSpec(PriceKind.EXACT, D("15"), D("15"))
    sliding = PriceSpec(PriceKind.RANGE, D("10"), D("20"))
    open_ended = PriceSpec(PriceKind.RANGE, D("10"), None)

    def test_exact_price_is_one_person(self):
        assert people_for_amount(self.exact, D("15.00")) == PeopleRange(1, 1)

    def test_exact_whole_multiple_is_several_people(self):
        assert people_for_amount(self.exact, D("45")) == PeopleRange(3, 3)

    @pytest.mark.parametrize("amount", ["14.99", "20", "7.50", "0", "-15"])
    def test_exact_non_multiple_does_not_fit(self, amount):
        assert people_for_amount(self.exact, D(amount)) is None

    @pytest.mark.parametrize("amount", ["10", "15", "19.99"])
    def test_range_accepts_any_amount_inside_it(self, amount):
        assert people_for_amount(self.sliding, D(amount)) == PeopleRange(1, 1)

    def test_range_top_amount_could_be_one_or_two_low_end_payers(self):
        assert people_for_amount(self.sliding, D("20")) == PeopleRange(1, 2)

    def test_range_multiple_of_in_range_amount_spans_head_counts(self):
        assert people_for_amount(self.sliding, D("40")) == PeopleRange(2, 4)

    def test_range_amount_splitting_into_in_range_shares_fits(self):
        assert people_for_amount(self.sliding, D("25")) == PeopleRange(2, 2)

    def test_range_below_low_end_does_not_fit(self):
        assert people_for_amount(self.sliding, D("9.99")) is None

    def test_open_ended_range_counts_up_to_amount_over_low(self):
        assert people_for_amount(self.open_ended, D("35")) == PeopleRange(1, 3)

    def test_unparseable_price_never_fits(self):
        assert people_for_amount(PriceSpec(PriceKind.UNPARSEABLE), D("15")) is None

    def test_people_range_includes_bounds(self):
        assert PeopleRange(2, 4).includes(2)
        assert PeopleRange(2, 4).includes(4)
        assert not PeopleRange(2, 4).includes(5)
