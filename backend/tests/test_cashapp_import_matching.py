from community._cashapp_import_filter import filter_payments
from community._cashapp_import_matching import match_payments
from community._cashapp_import_price import parse_event_price
from community._cashapp_import_types import MatchConfidence, MatchSource
from community.models import RSVPStatus

from tests._cashapp_helpers import event_ctx, guest, row

ALEX = guest("u-alex", "Alex", "Kim")
JAMIE = guest("u-jamie", "Jamie", "Lee")
SAM = guest("u-sam", "Samantha", "Ortiz", nickname="Sam")


def _match(rows, guests, price="$15"):
    result = filter_payments(rows, event_ctx(price=price), parse_event_price(price))
    return match_payments(result.kept, guests)


class TestSenderMatch:
    def test_unique_sender_and_single_price_is_confident(self):
        [p] = _match([row(sender="Alex Kim")], [ALEX, JAMIE])
        assert p.confidence == MatchConfidence.CONFIDENT
        assert p.user_ids == ["u-alex"]
        assert p.matched_by == MatchSource.SENDER
        assert p.reason == "sender name matches"

    def test_sender_match_ignores_case_accents_and_punctuation(self):
        jose = guest("u-jose", "José", "O'Neil")
        [p] = _match([row(sender="  JOSE  o neil ")], [jose])
        assert p.user_ids == ["u-jose"]
        assert p.confidence == MatchConfidence.CONFIDENT

    def test_sender_matches_nickname_plus_last_name(self):
        [p] = _match([row(sender="Sam Ortiz")], [SAM])
        assert p.user_ids == ["u-sam"]

    def test_sender_matching_only_a_bare_nickname_is_unsure(self):
        [p] = _match([row(sender="sam")], [SAM])
        assert p.user_ids == ["u-sam"]
        assert p.confidence == MatchConfidence.UNSURE
        assert p.reason == "only a nickname matched the sender"

    def test_bare_nickname_sender_with_same_first_name_guest_is_unsure(self):
        alexandra = guest("u-alexandra", "Alexandra", "Smith", nickname="Alex")
        alex_jones = guest("u-jones", "Alex", "Jones")
        [p] = _match([row(sender="Alex")], [alexandra, alex_jones])
        assert p.confidence == MatchConfidence.UNSURE
        assert p.reason == "only a nickname matched the sender"

    def test_sender_first_name_alone_does_not_match(self):
        [p] = _match([row(sender="Alex")], [ALEX])
        assert p.confidence == MatchConfidence.UNMATCHED

    def test_double_amount_with_plus_one_is_confident(self):
        alex = guest("u-alex", "Alex", "Kim", has_plus_one=True)
        [p] = _match([row(sender="Alex Kim", amount="30")], [alex])
        assert p.confidence == MatchConfidence.CONFIDENT

    def test_double_amount_without_second_person_is_unsure(self):
        [p] = _match([row(sender="Alex Kim", amount="30")], [ALEX])
        assert p.confidence == MatchConfidence.UNSURE
        assert p.user_ids == ["u-alex"]
        assert p.reason == "amount covers 2 people, matched 1"

    def test_single_amount_with_plus_one_is_unsure(self):
        alex = guest("u-alex", "Alex", "Kim", has_plus_one=True)
        [p] = _match([row(sender="Alex Kim")], [alex])
        assert p.confidence == MatchConfidence.UNSURE

    def test_waitlisted_sender_is_unsure(self):
        alex = guest("u-alex", "Alex", "Kim", status=RSVPStatus.WAITLISTED)
        [p] = _match([row(sender="Alex Kim")], [alex])
        assert p.confidence == MatchConfidence.UNSURE
        assert p.user_ids == ["u-alex"]
        assert p.reason == "guest is waitlisted"

    def test_non_matchable_statuses_are_ignored(self):
        alex = guest("u-alex", "Alex", "Kim", status=RSVPStatus.CANT_GO)
        [p] = _match([row(sender="Alex Kim")], [alex])
        assert p.confidence == MatchConfidence.UNMATCHED

    def test_refunded_payment_is_at_most_unsure(self):
        refund = row(index=1, amount="-15", sender="Alex Kim")
        [p] = _match([row(sender="Alex Kim"), refund], [ALEX])
        assert p.confidence == MatchConfidence.UNSURE
        assert p.reason == "refunded?"

    def test_range_price_amount_in_range_is_confident(self):
        [p] = _match([row(sender="Alex Kim", amount="12")], [ALEX], price="$10-20 sliding scale")
        assert p.confidence == MatchConfidence.CONFIDENT
        assert (p.people_low, p.people_high) == (1, 1)


class TestNoteMatch:
    def test_note_names_guest_when_sender_is_not_a_guest(self):
        [p] = _match([row(sender="Pat Kim", note="for jamie lee")], [ALEX, JAMIE])
        assert p.confidence == MatchConfidence.CONFIDENT
        assert p.user_ids == ["u-jamie"]
        assert p.matched_by == MatchSource.NOTE
        assert p.reason == "note names the guest"

    def test_note_naming_several_guests_covers_them_all(self):
        rows = [row(sender="Pat Kim", note="alex kim + jamie lee", amount="30")]
        [p] = _match(rows, [ALEX, JAMIE, SAM])
        assert p.confidence == MatchConfidence.CONFIDENT
        assert sorted(p.user_ids) == ["u-alex", "u-jamie"]

    def test_note_naming_more_guests_than_amount_covers_is_unsure(self):
        [p] = _match([row(sender="Pat Kim", note="alex kim, jamie lee")], [ALEX, JAMIE])
        assert p.confidence == MatchConfidence.UNSURE
        assert p.reason == "amount covers 1 person, matched 2"

    def test_sender_guest_paying_for_note_guest_covers_both(self):
        rows = [row(sender="Alex Kim", note="me and jamie lee", amount="30")]
        [p] = _match(rows, [ALEX, JAMIE])
        assert p.confidence == MatchConfidence.CONFIDENT
        assert p.user_ids == ["u-alex", "u-jamie"]
        assert p.matched_by == MatchSource.SENDER_AND_NOTE

    def test_attending_sender_with_first_name_of_other_guest_in_note_is_unsure(self):
        [p] = _match([row(sender="Alex Kim", note="for jamie")], [ALEX, JAMIE])
        assert p.confidence == MatchConfidence.UNSURE
        assert p.user_ids == ["u-alex"]
        assert p.candidate_user_ids == ["u-jamie"]
        assert p.reason == "note also names another guest"

    def test_attending_sender_with_ambiguous_full_name_in_note_is_unsure(self):
        twins = [guest("u-j1", "Jamie", "Lee"), guest("u-j2", "Jamie", "Lee")]
        [p] = _match([row(sender="Alex Kim", note="for jamie lee")], [ALEX, *twins])
        assert p.confidence == MatchConfidence.UNSURE
        assert sorted(p.candidate_user_ids) == ["u-j1", "u-j2"]
        assert p.reason == "note also names another guest"

    def test_note_guest_plus_another_first_name_is_unsure(self):
        [p] = _match([row(sender="Pat Kim", note="jamie lee and alex")], [ALEX, JAMIE])
        assert p.confidence == MatchConfidence.UNSURE
        assert p.user_ids == ["u-jamie"]
        assert p.candidate_user_ids == ["u-alex"]
        assert p.reason == "note also names another guest"

    def test_sliding_scale_multi_guest_with_variable_head_count_is_unsure(self):
        rows = [row(sender="Alex Kim", note="jamie lee told me", amount="20")]
        [p] = _match(rows, [ALEX, JAMIE], price="$10-20")
        assert p.confidence == MatchConfidence.UNSURE
        assert p.reason == "amount could cover 1-2 people"

    def test_open_ended_multi_guest_with_variable_head_count_is_unsure(self):
        rows = [row(sender="Alex Kim", note="hi jamie lee", amount="25")]
        [p] = _match(rows, [ALEX, JAMIE], price="$10+")
        assert p.confidence == MatchConfidence.UNSURE
        assert p.reason == "amount could cover 1-2 people"

    def test_sliding_scale_single_guest_with_plus_one_is_unsure(self):
        alex = guest("u-alex", "Alex", "Kim", has_plus_one=True)
        [p] = _match([row(sender="Alex Kim", amount="20")], [alex], price="$10-20")
        assert p.confidence == MatchConfidence.UNSURE
        assert p.reason == "amount could cover 1-2 people"

    def test_waitlisted_sender_whose_note_names_another_guest_is_unsure(self):
        bob = guest("u-bob", "Bob", "Lee", status=RSVPStatus.WAITLISTED)
        jane = guest("u-jane", "Jane", "Doe")
        [p] = _match([row(sender="Bob Lee", note="with jane doe")], [bob, jane])
        assert p.confidence == MatchConfidence.UNSURE
        assert p.reason == "sender is waitlisted; note names another guest"
        assert (p.user_ids, p.candidate_user_ids) == (["u-jane"], ["u-bob"])

    def test_nickname_only_waitlisted_sender_whose_note_names_another_guest_is_unsure(self):
        robert = guest("u-rob", "Robert", "Lee", nickname="Bob", status=RSVPStatus.WAITLISTED)
        jane = guest("u-jane", "Jane", "Doe")
        [p] = _match([row(sender="Bob", note="with jane doe")], [robert, jane])
        assert p.confidence == MatchConfidence.UNSURE
        assert p.reason == "sender is waitlisted; note names another guest"
        assert (p.user_ids, p.candidate_user_ids) == (["u-jane"], ["u-rob"])

    def test_note_with_nickname_and_last_name_matches(self):
        [p] = _match([row(sender="Pat Kim", note="sam ortiz's ticket")], [SAM])
        assert p.user_ids == ["u-sam"]

    def test_first_name_only_in_note_is_unsure_candidate(self):
        [p] = _match([row(sender="Pat Kim", note="for jamie!")], [ALEX, JAMIE])
        assert p.confidence == MatchConfidence.UNSURE
        assert p.user_ids == []
        assert p.candidate_user_ids == ["u-jamie"]
        assert p.reason == "only a first name in the note matched"

    def test_no_sender_or_note_match_is_unmatched(self):
        [p] = _match([row(sender="Pat Kim", note="dinner")], [ALEX, JAMIE])
        assert p.confidence == MatchConfidence.UNMATCHED
        assert p.matched_by == MatchSource.NONE
        assert p.user_ids == []
        assert p.reason == "no guest matches the sender or note"


class TestAmbiguity:
    def test_sender_matching_two_guests_is_unsure_with_candidates(self):
        twins = [guest("u-a1", "Alex", "Kim"), guest("u-a2", "Alex", "Kim")]
        [p] = _match([row(sender="Alex Kim")], twins)
        assert p.confidence == MatchConfidence.UNSURE
        assert p.user_ids == []
        assert sorted(p.candidate_user_ids) == ["u-a1", "u-a2"]
        assert p.reason == "sender name matches several guests"

    def test_note_name_matching_two_guests_is_unsure(self):
        twins = [guest("u-j1", "Jamie", "Lee"), guest("u-j2", "Jamie", "Lee")]
        [p] = _match([row(sender="Pat Kim", note="for jamie lee")], twins)
        assert p.confidence == MatchConfidence.UNSURE
        assert sorted(p.candidate_user_ids) == ["u-j1", "u-j2"]
        assert p.reason == "note name matches several guests"

    def test_two_payments_for_one_guest_are_both_unsure(self):
        rows = [row(index=0, sender="Alex Kim"), row(index=1, sender="Pat Kim", note="alex kim")]
        proposals = _match(rows, [ALEX])
        assert [p.confidence for p in proposals] == [MatchConfidence.UNSURE] * 2
        assert {p.reason for p in proposals} == {"guest also matched another payment"}

    def test_unparseable_price_is_never_confident(self):
        [p] = _match([row(sender="Alex Kim", amount="22")], [ALEX], price="pay what you can")
        assert p.confidence == MatchConfidence.UNSURE
        assert p.user_ids == ["u-alex"]
        assert p.reason == "price couldn't be read"
        assert (p.people_low, p.people_high) == (None, None)
