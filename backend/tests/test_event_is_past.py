from datetime import timedelta

import pytest
from community._cohost_invite_helpers import expire_stale_cohost_invites
from community.models import CoHostInviteStatus, Event, EventCoHostInvite
from community.models.event import _is_past_q
from django.utils import timezone


def _event(start=None, end=None, **extra) -> Event:
    return Event.objects.create(title="e", start_datetime=start, end_datetime=end, **extra)


CASES = [
    ("ended", {"start": -3, "end": -1}, True),
    ("running", {"start": -1, "end": 1}, False),
    ("no end, started 1h ago", {"start": -1}, False),
    ("no end, started 3h ago", {"start": -3}, True),
    ("no end, starts later", {"start": 1}, False),
    ("tbd", {"datetime_tbd": True}, False),
]


def _build(spec: dict) -> Event:
    now = timezone.now()
    start = now + timedelta(hours=spec["start"]) if "start" in spec else None
    end = now + timedelta(hours=spec["end"]) if "end" in spec else None
    return _event(start, end, datetime_tbd=spec.get("datetime_tbd", False))


@pytest.mark.django_db
class TestIsPast:
    @pytest.mark.parametrize(
        ("spec", "expected"), [c[1:] for c in CASES], ids=[c[0] for c in CASES]
    )
    def test_property_and_queryset_agree(self, spec, expected):
        event = _build(spec)
        assert event.is_past is expected
        in_past_q = Event.objects.filter(_is_past_q(timezone.now()), pk=event.pk).exists()
        assert in_past_q is expected


@pytest.mark.django_db
class TestLazyExpireNoEnd:
    def _invite(self, event: Event, test_user) -> EventCoHostInvite:
        return EventCoHostInvite.objects.create(
            event=event, user=test_user, status=CoHostInviteStatus.PENDING
        )

    def test_expires_two_hours_after_start(self, test_user):
        invite = self._invite(_build({"start": -3}), test_user)
        expire_stale_cohost_invites(invite.event)
        invite.refresh_from_db()
        assert invite.status == CoHostInviteStatus.EXPIRED

    def test_stays_pending_within_two_hours_of_start(self, test_user):
        invite = self._invite(_build({"start": -1}), test_user)
        expire_stale_cohost_invites(invite.event)
        invite.refresh_from_db()
        assert invite.status == CoHostInviteStatus.PENDING
