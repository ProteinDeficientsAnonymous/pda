from datetime import timedelta
from decimal import Decimal

import pytest
from community._cashapp_import_filter import filter_payments
from community._cashapp_import_price import PeopleRange, parse_event_price
from community._cashapp_import_types import FilterReason

from tests._cashapp_helpers import CREATED, ENDS, IN_WINDOW, event_ctx, row


def _result(rows, price="$15", **ctx):
    return filter_payments(rows, event_ctx(price=price, **ctx), parse_event_price(price))


def _run(rows, price="$15", **ctx):
    result = _result(rows, price, **ctx)
    return result.kept, result.dropped


class TestStatusAndDirection:
    @pytest.mark.parametrize("status", ["COMPLETE", "COMPLETED", "PAYMENT_DEPOSITED"])
    def test_completed_statuses_are_kept(self, status):
        kept, dropped = _run([row(status=status)])
        assert len(kept) == 1
        assert not dropped

    @pytest.mark.parametrize("status", ["CANCELED", "FAILED", "REFUNDED", "PAYMENT_SENT", ""])
    def test_other_statuses_are_dropped_as_not_completed(self, status):
        kept, dropped = _run([row(status=status)])
        assert kept == []
        assert dropped == {FilterReason.NOT_COMPLETED: 1}

    def test_outgoing_payment_is_dropped(self):
        _, dropped = _run([row(amount="-15", status="PAYMENT_SENT")])
        assert dropped == {FilterReason.OUTGOING: 1}

    @pytest.mark.parametrize(
        "tx_type",
        [
            "Cash In",
            "Direct Deposit",
            "Paper Money Deposit",
            "Check Deposit",
            "Refund",
            "Interest Payment",
            "Bitcoin Sale",
            "boost",
        ],
    )
    def test_non_peer_transaction_types_are_dropped(self, tx_type):
        _, dropped = _run([row(tx_type=tx_type)])
        assert dropped == {FilterReason.NOT_PEER_PAYMENT: 1}

    @pytest.mark.parametrize("tx_type", ["P2P", "Cash Card", "Received P2P", ""])
    def test_unknown_or_peer_types_are_kept(self, tx_type):
        kept, _ = _run([row(tx_type=tx_type)])
        assert len(kept) == 1

    def test_unreadable_amount_or_date_is_counted_and_returned(self):
        result = _result([row(amount=None), row(index=1, paid_at=None)])
        assert result.dropped == {FilterReason.UNREADABLE: 2}
        assert [r.row_index for r in result.unreadable] == [0, 1]

    def test_duplicate_of_a_dropped_row_still_counts_as_duplicate(self):
        result = _result([row(tx="abc", amount="7"), row(index=1, tx="abc", amount="7")])
        assert result.dropped == {FilterReason.AMOUNT_MISMATCH: 1, FilterReason.DUPLICATE: 1}
        assert len(result.amount_mismatches) == 1

    def test_repeated_transaction_id_is_dropped_as_duplicate(self):
        kept, dropped = _run([row(tx="abc"), row(index=1, tx="abc")])
        assert [k.row.row_index for k in kept] == [0]
        assert dropped == {FilterReason.DUPLICATE: 1}


class TestWindow:
    def test_payment_at_event_creation_is_kept(self):
        kept, _ = _run([row(paid_at=CREATED)])
        assert len(kept) == 1

    def test_payment_just_before_creation_is_dropped(self):
        _, dropped = _run([row(paid_at=CREATED - timedelta(seconds=1))])
        assert dropped == {FilterReason.BEFORE_EVENT_CREATED: 1}

    def test_payment_at_event_end_is_kept(self):
        kept, _ = _run([row(paid_at=ENDS)])
        assert len(kept) == 1

    def test_payment_just_after_end_is_dropped(self):
        _, dropped = _run([row(paid_at=ENDS + timedelta(seconds=1))])
        assert dropped == {FilterReason.AFTER_EVENT_ENDED: 1}

    def test_no_end_means_no_upper_bound(self):
        kept, _ = _run([row(paid_at=ENDS + timedelta(days=30))], ends_at=None)
        assert len(kept) == 1


class TestAmountFilter:
    def test_exact_price_is_one_person(self):
        kept, _ = _run([row(amount="15")])
        assert kept[0].people == PeopleRange(1, 1)

    def test_whole_multiple_of_exact_price_is_kept(self):
        kept, _ = _run([row(amount="30.00")])
        assert kept[0].people == PeopleRange(2, 2)

    def test_non_multiple_is_dropped_as_amount_mismatch_and_returned(self):
        result = _result([row(amount="20")])
        assert result.dropped == {FilterReason.AMOUNT_MISMATCH: 1}
        assert [m.amount for m in result.amount_mismatches] == [Decimal("20")]

    def test_range_price_keeps_amount_in_range(self):
        kept, _ = _run([row(amount="12")], price="$10-20 sliding scale")
        assert kept[0].people == PeopleRange(1, 1)

    def test_range_price_keeps_multiple_of_in_range_amount(self):
        kept, _ = _run([row(amount="40")], price="$10-20 sliding scale")
        assert kept[0].people == PeopleRange(2, 4)

    def test_range_price_drops_amount_below_range(self):
        _, dropped = _run([row(amount="5")], price="$10-20 sliding scale")
        assert dropped == {FilterReason.AMOUNT_MISMATCH: 1}

    def test_unparseable_price_keeps_any_amount_without_head_count(self):
        kept, dropped = _run([row(amount="7"), row(index=1, amount="300")], price="pwyc")
        assert [k.people for k in kept] == [None, None]
        assert not dropped

    def test_counts_cover_every_dropped_row(self):
        rows = [
            row(index=0),
            row(index=1, amount="-15"),
            row(index=2, status="FAILED"),
            row(index=3, amount="16"),
            row(index=4, paid_at=CREATED - timedelta(days=1)),
        ]
        kept, dropped = _run(rows)
        assert len(kept) + sum(dropped.values()) == len(rows)


class TestRefunds:
    def test_later_outgoing_to_same_sender_for_same_amount_marks_refunded(self):
        refund = row(
            index=1, amount="-15", sender="alex kim", paid_at=IN_WINDOW + timedelta(hours=1)
        )
        kept, _ = _run([row(sender="Alex Kim"), refund])
        assert kept[0].refunded

    def test_outgoing_before_the_payment_is_not_a_refund(self):
        earlier = row(index=1, amount="-15", paid_at=IN_WINDOW - timedelta(hours=1))
        kept, _ = _run([row(), earlier])
        assert not kept[0].refunded

    def test_later_partial_refund_to_the_sender_marks_refunded(self):
        partial = row(index=1, amount="-5", paid_at=IN_WINDOW + timedelta(hours=1))
        kept, _ = _run([row(), partial])
        assert kept[0].refunded

    def test_later_outgoing_to_someone_else_is_not_a_refund(self):
        other = row(index=1, amount="-15", sender="Sam Lee", paid_at=IN_WINDOW + timedelta(hours=1))
        kept, _ = _run([row(), other])
        assert not kept[0].refunded

    def test_failed_outgoing_is_not_a_refund(self):
        failed = row(index=1, amount="-15", status="FAILED", paid_at=IN_WINDOW + timedelta(hours=1))
        kept, _ = _run([row(), failed])
        assert not kept[0].refunded
