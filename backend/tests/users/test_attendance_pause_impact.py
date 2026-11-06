from datetime import timedelta

import pytest
from community.models import Event, EventRSVP, EventStatus, EventType, RSVPStatus
from django.utils import timezone
from users._archive import _release_upcoming_rsvps, _step_down_as_cohost
from users._attendance_pause import QUALIFYING_EVENT_Q, attendance_pause_impact
from users.models import User


def _event(creator: User, event_type=EventType.COMMUNITY, *, days: int = 3, **extra) -> Event:
    return Event.objects.create(
        title=f"{event_type} event",
        event_type=event_type,
        start_datetime=timezone.now() + timedelta(days=days),
        created_by=creator,
        **extra,
    )


def _rsvp(event: Event, user: User, status=RSVPStatus.ATTENDING) -> EventRSVP:
    return EventRSVP.objects.create(event=event, user=user, status=status)


@pytest.mark.django_db
class TestAttendancePauseImpact:
    @pytest.mark.parametrize("event_type", [EventType.OFFICIAL, EventType.CLUB])
    def test_keeps_qualifying_rsvps(self, member, other_user, event_type):
        event = _event(other_user, event_type)
        _rsvp(event, member)
        assert attendance_pause_impact(member).kept_rsvps == [event]

    @pytest.mark.parametrize(
        "status", [RSVPStatus.ATTENDING, RSVPStatus.MAYBE, RSVPStatus.WAITLISTED]
    )
    def test_removes_other_rsvps(self, member, other_user, status):
        event = _event(other_user)
        _rsvp(event, member, status)
        assert attendance_pause_impact(member).removed_rsvps == [event]

    def test_ignores_cant_go_rsvps(self, member, other_user):
        _rsvp(_event(other_user), member, RSVPStatus.CANT_GO)
        assert attendance_pause_impact(member).removed_rsvps == []

    @pytest.mark.parametrize("co_hosted", [True, False])
    def test_keeps_qualifying_hosting(self, member, other_user, co_hosted):
        event = _event(member, EventType.OFFICIAL)
        if co_hosted:
            event.co_hosts.add(other_user)
        assert attendance_pause_impact(member).kept_hosting == [event]

    def test_removes_shared_hosting(self, member, other_user):
        event = _event(other_user)
        event.co_hosts.add(member)
        assert attendance_pause_impact(member).removed_hosting == [event]

    def test_drafts_sole_hosted_events(self, member):
        event = _event(member)
        assert attendance_pause_impact(member).drafted_events == [event]

    def test_drafted_event_rsvp_is_not_listed_as_removed(self, member):
        event = _event(member)
        _rsvp(event, member)
        impact = attendance_pause_impact(member)
        assert impact.drafted_events == [event]
        assert impact.removed_rsvps == []

    def test_excludes_past_events(self, member, other_user):
        _rsvp(_event(other_user, days=-3), member)
        _event(member, days=-3)
        impact = attendance_pause_impact(member)
        assert impact.removed_rsvps == []
        assert impact.drafted_events == []

    def test_excludes_cancelled_events(self, member, other_user):
        _rsvp(_event(other_user, status=EventStatus.CANCELLED), member)
        assert attendance_pause_impact(member).removed_rsvps == []

    def test_orders_soonest_first(self, member, other_user):
        later = _event(other_user, days=9)
        sooner = _event(other_user, days=2)
        _rsvp(later, member)
        _rsvp(sooner, member)
        assert attendance_pause_impact(member).removed_rsvps == [sooner, later]


@pytest.mark.django_db
class TestArchiveHelperEventFilter:
    def test_release_skips_events_outside_filter(self, rf, member, other_user):
        official = _event(other_user, EventType.OFFICIAL)
        community = _event(other_user)
        _rsvp(official, member)
        _rsvp(community, member)

        _release_upcoming_rsvps(rf.get("/"), member, ~QUALIFYING_EVENT_Q)

        assert EventRSVP.objects.get(event=official, user=member).status == RSVPStatus.ATTENDING
        assert EventRSVP.objects.get(event=community, user=member).status == RSVPStatus.CANT_GO

    def test_step_down_skips_events_outside_filter(self, member, other_user):
        official = _event(other_user, EventType.OFFICIAL)
        community = _event(other_user)
        official.co_hosts.add(member)
        community.co_hosts.add(member)

        _step_down_as_cohost(member, ~QUALIFYING_EVENT_Q)

        assert official.co_hosts.filter(pk=member.pk).exists()
        assert not community.co_hosts.filter(pk=member.pk).exists()
