"""Unit tests for event helper functions (is_cohost, _build_guest_list, _find_my_rsvp)."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from community.api import _build_guest_list, _find_my_rsvp, is_cohost
from community.models import AttendanceStatus, RSVPStatus


class TestIsCohost:
    def test_returns_false_when_no_requesting_user(self):
        assert is_cohost(None, {"id1"}) is False

    def test_returns_true_when_user_is_co_host(self):
        requesting = MagicMock()
        requesting.pk = "user-2"
        assert is_cohost(requesting, {"user-2"}) is True

    def test_returns_false_when_user_is_not_a_co_host(self):
        requesting = MagicMock()
        requesting.pk = "user-3"
        assert is_cohost(requesting, {"user-2"}) is False


class TestBuildGuestList:
    def _make_rsvp(self, user_id, name, status, phone, show_phone=True):
        return SimpleNamespace(
            user_id=user_id,
            user=SimpleNamespace(
                id=user_id,
                first_name=name or "",
                last_name="",
                full_name=name or "",
                phone_number=phone,
                show_phone=show_phone,
                profile_photo=None,
                hide_last_name=False,
                is_member=True,
            ),
            status=status,
            has_plus_one=False,
            attendance=AttendanceStatus.UNKNOWN,
            checked_in_at=None,
            plus_one_attendance=AttendanceStatus.UNKNOWN,
            plus_one_checked_in_at=None,
            paid_confirmed_at=None,
        )

    def test_empty_rsvps(self):
        assert _build_guest_list([], can_see_phones=True) == []

    def test_hides_phones_when_not_allowed(self):
        rsvp = self._make_rsvp("u1", "Alice", RSVPStatus.ATTENDING, "+1555000")
        result = _build_guest_list([rsvp], can_see_phones=False)
        assert result[0].phone is None

    def test_shows_phones_when_allowed(self):
        rsvp = self._make_rsvp("u1", "Alice", RSVPStatus.ATTENDING, "+1555000")
        result = _build_guest_list([rsvp], can_see_phones=True)
        assert result[0].phone == "+1555000"

    def test_uses_phone_as_name_fallback(self):
        rsvp = self._make_rsvp("u1", None, RSVPStatus.ATTENDING, "+1555000")
        result = _build_guest_list([rsvp], can_see_phones=False)
        assert result[0].name == "+1555000"

    def test_nameless_private_phone_falls_back_to_member(self):
        rsvp = self._make_rsvp("u1", None, RSVPStatus.ATTENDING, "+1555000", show_phone=False)
        result = _build_guest_list([rsvp], can_see_phones=False)
        assert result[0].name == "member"

    def test_includes_questionnaire_responses_only_when_requested(self):
        rsvp = self._make_rsvp("u1", "Alice", RSVPStatus.ATTENDING, "+1555000")
        rsvp.questionnaire_responses = {"qid": {"label": "q", "answer": "yes"}}
        hidden = _build_guest_list(
            [rsvp], can_see_phones=False, include_questionnaire_responses=False
        )
        assert hidden[0].questionnaire_responses == {}
        shown = _build_guest_list(
            [rsvp], can_see_phones=False, include_questionnaire_responses=True
        )
        assert shown[0].questionnaire_responses == {"qid": {"label": "q", "answer": "yes"}}


class TestFindMyRsvp:
    def _make_rsvp(self, user_id, status):
        return SimpleNamespace(user_id=user_id, status=status)

    def test_returns_none_when_no_user(self):
        assert _find_my_rsvp([self._make_rsvp("u1", RSVPStatus.ATTENDING)], None) is None

    def test_returns_none_when_user_not_in_rsvps(self):
        user = SimpleNamespace(pk="u2")
        assert _find_my_rsvp([self._make_rsvp("u1", RSVPStatus.ATTENDING)], user) is None

    def test_returns_row_when_user_found(self):
        user = SimpleNamespace(pk="u1")
        assert (
            _find_my_rsvp([self._make_rsvp("u1", RSVPStatus.MAYBE)], user).status
            == RSVPStatus.MAYBE
        )

    def test_returns_first_match(self):
        user = SimpleNamespace(pk="u1")
        rsvps = [
            self._make_rsvp("u1", RSVPStatus.ATTENDING),
            self._make_rsvp("u1", RSVPStatus.MAYBE),
        ]
        assert _find_my_rsvp(rsvps, user).status == RSVPStatus.ATTENDING
