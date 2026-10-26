from datetime import timedelta

import pytest
from community._cashapp_import_price import PriceKind
from community._cashapp_import_review import (
    NO_END_GRACE,
    load_guests_and_verified,
    load_payment_context,
    review_cashapp_csv,
)
from community._cashapp_import_types import GapReason, MatchConfidence
from community.models import EventRSVP, RSVPStatus
from django.utils import timezone
from users.models import User

from tests._cashapp_helpers import csv_line, event_ctx, guest, make_csv
from tests._payment_helpers import create_paid_event

ALEX = guest("u-alex", "Alex", "Kim", said_paid=True)
JAMIE = guest("u-jamie", "Jamie", "Lee", said_paid=True)
SAM = guest("u-sam", "Sam", "Ortiz")
WAITLISTED = guest("u-wait", "Wren", "Park", status=RSVPStatus.WAITLISTED)


def _csv():
    return make_csv(
        csv_line(tx="t1", name="Alex Kim"),
        csv_line(tx="t2", name="Pat Doe", note="dinner"),
        csv_line(tx="t3", name="Alex Kim", status="FAILED"),
        csv_line(tx="t4", name="Rent Co", amount="-$40"),
        csv_line(tx="t5", name="Alex Kim", amount="$16"),
        csv_line(tx="t6", name="Alex Kim", date="2026-01-01 10:00:00 EST"),
    )


class TestReview:
    def test_end_to_end_counts_proposals_and_filters(self):
        review = review_cashapp_csv(_csv(), event_ctx(), [ALEX, JAMIE, SAM])
        assert review.total_rows == 6
        assert review.price.kind == PriceKind.EXACT
        assert [(p.payment_id, p.confidence) for p in review.proposals] == [
            ("t1", MatchConfidence.CONFIDENT),
            ("t2", MatchConfidence.UNMATCHED),
        ]
        assert review.filtered == {
            "not_completed": 1,
            "outgoing": 1,
            "amount_mismatch": 1,
            "before_event_created": 1,
        }
        assert review.unplaced_payment_ids == ["t2"]

    def test_gap_lists_said_paid_first_then_attending_on_paid_event(self):
        review = review_cashapp_csv(_csv(), event_ctx(), [ALEX, JAMIE, SAM, WAITLISTED])
        gaps = [(g.user_id, g.reason) for g in review.gap_guests]
        assert gaps == [
            ("u-jamie", GapReason.SAID_PAID),
            ("u-sam", GapReason.ATTENDING_PAID_EVENT),
        ]

    def test_waitlisted_guest_who_said_paid_is_in_gap(self):
        wren = guest("u-wait", "Wren", "Park", status=RSVPStatus.WAITLISTED, said_paid=True)
        review = review_cashapp_csv(_csv(), event_ctx(), [wren])
        assert [g.user_id for g in review.gap_guests] == ["u-wait"]

    def test_attending_guest_on_unpaid_event_is_not_a_gap(self):
        review = review_cashapp_csv(_csv(), event_ctx(is_paid_event=False), [SAM])
        assert review.gap_guests == []

    def test_already_verified_guests_are_left_out_of_gap(self):
        review = review_cashapp_csv(_csv(), event_ctx(), [JAMIE, SAM], {"u-jamie", "u-sam"})
        assert review.gap_guests == []

    def test_partial_refund_to_the_guest_keeps_them_pending(self):
        csv_text = make_csv(
            csv_line(tx="t1", name="Alex Kim"),
            csv_line(tx="t2", name="Alex Kim", amount="-$5", date="2026-10-02 18:00:00 EDT"),
        )
        review = review_cashapp_csv(csv_text, event_ctx(), [ALEX])
        assert (review.proposals[0].confidence, review.proposals[0].reason) == (
            MatchConfidence.UNSURE,
            "refunded?",
        )
        assert [g.reason for g in review.gap_guests] == [GapReason.UNSURE_MATCH_PENDING]

    def test_unsure_match_stays_in_gap_as_pending(self):
        alex = guest("u-alex", "Alex", "Kim", has_plus_one=True, said_paid=True)
        review = review_cashapp_csv(_csv(), event_ctx(), [alex])
        assert review.proposals[0].confidence == MatchConfidence.UNSURE
        [gap] = review.gap_guests
        assert gap.user_id == "u-alex"
        assert gap.reason == GapReason.UNSURE_MATCH_PENDING
        assert gap.pending_payment_ids == ["t1"]
        assert gap.said_paid

    def test_ambiguous_candidates_stay_in_gap_as_pending(self):
        twins = [
            guest("u-a1", "Alex", "Kim", said_paid=True),
            guest("u-a2", "Alex", "Kim", said_paid=True),
        ]
        review = review_cashapp_csv(_csv(), event_ctx(), twins)
        assert {g.user_id for g in review.gap_guests} == {"u-a1", "u-a2"}
        assert {g.reason for g in review.gap_guests} == {GapReason.UNSURE_MATCH_PENDING}

    def test_unreadable_rows_are_surfaced(self):
        csv = make_csv(csv_line(tx="t1", amount="lots", name="Alex Kim"))
        review = review_cashapp_csv(csv, event_ctx(), [ALEX])
        [bad] = review.unreadable_rows
        assert (bad.payment_id, bad.row_index, bad.sender_name) == ("t1", 0, "Alex Kim")
        assert (bad.raw_amount, bad.raw_date) == ("lots", "2026-10-01 18:22:11 EDT")

    def test_amount_mismatch_from_a_guest_is_a_lead(self):
        review = review_cashapp_csv(_csv(), event_ctx(), [ALEX, JAMIE])
        [lead] = review.amount_mismatch_leads
        assert lead.payment_id == "t5"
        assert lead.user_ids == ["u-alex"]

    def test_amount_mismatch_from_a_stranger_is_not_a_lead(self):
        csv = make_csv(csv_line(tx="t1", amount="$16", name="Pat Doe"))
        assert review_cashapp_csv(csv, event_ctx(), [ALEX]).amount_mismatch_leads == []

    def test_unparseable_price_keeps_payments_for_review(self):
        csv = make_csv(csv_line(tx="t1", amount="$22", name="Alex Kim"))
        review = review_cashapp_csv(csv, event_ctx(price="pay what you can"), [ALEX])
        assert review.price.kind == PriceKind.UNPARSEABLE
        assert review.proposals[0].confidence == MatchConfidence.UNSURE
        assert review.filtered == {}


@pytest.mark.django_db
class TestLoaders:
    def _user(self, phone, first, last, nickname=""):
        return User.objects.create_user(
            phone_number=phone, first_name=first, last_name=last, nickname=nickname
        )

    def test_guest_records_cover_attending_and_waitlisted_only(self):
        event = create_paid_event(price="$15")
        alex = self._user("+12025550201", "Alex", "Kim", nickname="Al")
        wren = self._user("+12025550202", "Wren", "Park")
        gone = self._user("+12025550203", "Gone", "Person")
        EventRSVP.objects.create(
            event=event,
            user=alex,
            status=RSVPStatus.ATTENDING,
            has_plus_one=True,
            paid_confirmed_at=timezone.now(),
        )
        EventRSVP.objects.create(event=event, user=wren, status=RSVPStatus.WAITLISTED)
        EventRSVP.objects.create(event=event, user=gone, status=RSVPStatus.CANT_GO)

        records = {r.user_id: r for r in load_guests_and_verified(event)[0]}

        assert set(records) == {str(alex.id), str(wren.id)}
        a = records[str(alex.id)]
        assert (a.first_name, a.last_name, a.nickname) == ("Alex", "Kim", "Al")
        assert a.has_plus_one and a.said_paid
        assert records[str(wren.id)].status == RSVPStatus.WAITLISTED
        assert not records[str(wren.id)].said_paid

    def test_verified_ids_include_verified_non_guests(self):
        event = create_paid_event(price="$15")
        alex = self._user("+12025550201", "Alex", "Kim")
        gone = self._user("+12025550203", "Gone", "Person")
        verified_at = timezone.now()
        EventRSVP.objects.create(
            event=event, user=alex, status=RSVPStatus.ATTENDING, payment_verified_at=verified_at
        )
        EventRSVP.objects.create(
            event=event, user=gone, status=RSVPStatus.CANT_GO, payment_verified_at=verified_at
        )

        guests, verified = load_guests_and_verified(event)

        assert [g.user_id for g in guests] == [str(alex.id)]
        assert verified == {str(alex.id), str(gone.id)}

    def test_payment_context_uses_end_then_start(self):
        event = create_paid_event()
        ctx = load_payment_context(event)
        assert ctx.created_at == event.created_at
        assert ctx.ends_at == event.end_datetime
        assert ctx.is_paid_event

        event.end_datetime = None
        assert load_payment_context(event).ends_at == event.start_datetime + NO_END_GRACE

        event.start_datetime = None
        assert load_payment_context(event).ends_at is None

    def test_at_the_door_payment_after_start_is_kept_when_no_end(self):
        event = create_paid_event(price="$15", end_datetime=None)
        event.created_at = event.start_datetime - timedelta(days=7)
        alex = self._user("+12025550205", "Alex", "Kim")
        EventRSVP.objects.create(event=event, user=alex, status=RSVPStatus.ATTENDING)
        when = event.start_datetime + timedelta(hours=2)
        csv = make_csv(csv_line(date=when.strftime("%Y-%m-%d %H:%M:%S %z"), name="Alex Kim"))

        review = review_cashapp_csv(
            csv, load_payment_context(event), load_guests_and_verified(event)[0]
        )

        assert review.filtered == {}
        assert review.proposals[0].user_ids == [str(alex.id)]

    def test_priced_event_without_payment_link_still_counts_as_paid(self):
        event = create_paid_event(venmo_link="", price="$15")
        assert load_payment_context(event).is_paid_event

    def test_free_event_is_not_paid(self):
        event = create_paid_event(price="free", venmo_link="")
        assert not load_payment_context(event).is_paid_event

    def test_loaded_records_feed_the_review(self):
        event = create_paid_event(price="$15")
        event.created_at = timezone.now() - timedelta(days=1)
        alex = self._user("+12025550204", "Alex", "Kim")
        EventRSVP.objects.create(event=event, user=alex, status=RSVPStatus.ATTENDING)
        when = timezone.now().astimezone(timezone.get_default_timezone())
        csv = make_csv(csv_line(date=when.strftime("%Y-%m-%d %H:%M:%S %z"), name="Alex Kim"))

        review = review_cashapp_csv(
            csv, load_payment_context(event), load_guests_and_verified(event)[0]
        )

        assert review.proposals[0].user_ids == [str(alex.id)]
        assert review.proposals[0].confidence == MatchConfidence.CONFIDENT
