"""Unit tests for event helper functions (_can_see_phones, _build_guest_list, _find_my_rsvp)."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from community.api import _build_guest_list, _can_see_phones, _find_my_rsvp
from community.models import AttendanceStatus, RSVPStatus


class TestCanSeePhones:
    def test_returns_false_when_no_requesting_user(self):
        assert _can_see_phones(None, MagicMock(), {"id1"}) is False

    def test_returns_true_when_user_is_creator(self):
        creator = MagicMock()
        creator.pk = "user-1"
        requesting = MagicMock()
        requesting.pk = "user-1"
        assert _can_see_phones(requesting, creator, set()) is True

    def test_returns_true_when_user_is_co_host(self):
        creator = MagicMock()
        creator.pk = "user-1"
        requesting = MagicMock()
        requesting.pk = "user-2"
        assert _can_see_phones(requesting, creator, {"user-2"}) is True

    def test_returns_false_when_user_is_neither(self):
        creator = MagicMock()
        creator.pk = "user-1"
        requesting = MagicMock()
        requesting.pk = "user-3"
        assert _can_see_phones(requesting, creator, {"user-2"}) is False

    def test_returns_false_when_creator_is_none(self):
        requesting = MagicMock()
        requesting.pk = "user-1"
        assert _can_see_phones(requesting, None, set()) is False


class TestBuildGuestList:
    def _make_rsvp(self, user_id, name, status, phone):
        return SimpleNamespace(
            user_id=user_id,
            user=SimpleNamespace(display_name=name, phone_number=phone, profile_photo=None),
            status=status,
            has_plus_one=False,
            attendance=AttendanceStatus.UNKNOWN,
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


class TestFindMyRsvp:
    def _make_rsvp(self, user_id, status):
        return SimpleNamespace(user_id=user_id, status=status)

    def test_returns_none_when_no_user(self):
        assert _find_my_rsvp([self._make_rsvp("u1", RSVPStatus.ATTENDING)], None) is None

    def test_returns_none_when_user_not_in_rsvps(self):
        user = SimpleNamespace(pk="u2")
        assert _find_my_rsvp([self._make_rsvp("u1", RSVPStatus.ATTENDING)], user) is None

    def test_returns_status_when_user_found(self):
        user = SimpleNamespace(pk="u1")
        assert _find_my_rsvp([self._make_rsvp("u1", RSVPStatus.MAYBE)], user) == RSVPStatus.MAYBE

    def test_returns_first_match(self):
        user = SimpleNamespace(pk="u1")
        rsvps = [
            self._make_rsvp("u1", RSVPStatus.ATTENDING),
            self._make_rsvp("u1", RSVPStatus.MAYBE),
        ]
        assert _find_my_rsvp(rsvps, user) == RSVPStatus.ATTENDING
