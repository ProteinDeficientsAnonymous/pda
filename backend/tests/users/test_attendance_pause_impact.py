from datetime import timedelta

import pytest
from community.models import EventRSVP, EventStatus, EventType, RSVPStatus
from django.utils import timezone
from tests._events import make_event, make_rsvp
from users._archive import release_upcoming_rsvps, step_down_as_cohost
from users._attendance_pause import KEPT_EVENT_Q, attendance_pause_impact


def _in_days(days: int):
    return timezone.now() + timedelta(days=days)


@pytest.mark.django_db
class TestAttendancePauseImpact:
    @pytest.mark.parametrize("event_type", [EventType.OFFICIAL, EventType.CLUB])
    def test_keeps_official_and_club_rsvps(self, member, other_user, event_type):
        event = make_event(created_by=other_user, event_type=event_type)
        make_rsvp(event, member)
        assert attendance_pause_impact(member).kept_rsvps == [event]

    @pytest.mark.parametrize(
        "status", [RSVPStatus.ATTENDING, RSVPStatus.MAYBE, RSVPStatus.WAITLISTED]
    )
    def test_removes_other_rsvps(self, member, other_user, status):
        event = make_event(created_by=other_user)
        make_rsvp(event, member, status)
        assert attendance_pause_impact(member).removed_rsvps == [event]

    def test_ignores_cant_go_rsvps(self, member, other_user):
        make_rsvp(make_event(created_by=other_user), member, RSVPStatus.CANT_GO)
        assert attendance_pause_impact(member).removed_rsvps == []

    @pytest.mark.parametrize("co_hosted", [True, False])
    def test_keeps_official_and_club_hosting(self, member, other_user, co_hosted):
        event = make_event(created_by=member, event_type=EventType.OFFICIAL)
        if co_hosted:
            event.co_hosts.add(other_user)
        assert attendance_pause_impact(member).kept_hosting == [event]

    def test_removes_shared_hosting(self, member, other_user):
        event = make_event(created_by=other_user)
        event.co_hosts.add(member)
        assert attendance_pause_impact(member).removed_hosting == [event]

    def test_drafts_sole_hosted_events(self, member):
        event = make_event(created_by=member)
        assert attendance_pause_impact(member).drafted_events == [event]

    def test_drafted_event_rsvp_is_not_listed_as_removed(self, member):
        event = make_event(created_by=member)
        make_rsvp(event, member)
        impact = attendance_pause_impact(member)
        assert impact.drafted_events == [event]
        assert impact.removed_rsvps == []

    def test_excludes_past_events(self, member, other_user):
        make_rsvp(make_event(created_by=other_user, start_datetime=_in_days(-3)), member)
        make_event(created_by=member, start_datetime=_in_days(-3))
        impact = attendance_pause_impact(member)
        assert impact.removed_rsvps == []
        assert impact.drafted_events == []

    def test_excludes_cancelled_events(self, member, other_user):
        make_rsvp(make_event(created_by=other_user, status=EventStatus.CANCELLED), member)
        assert attendance_pause_impact(member).removed_rsvps == []

    def test_orders_soonest_first(self, member, other_user):
        later = make_event(created_by=other_user, start_datetime=_in_days(9))
        sooner = make_event(created_by=other_user, start_datetime=_in_days(2))
        make_rsvp(later, member)
        make_rsvp(sooner, member)
        assert attendance_pause_impact(member).removed_rsvps == [sooner, later]


@pytest.mark.django_db
class TestArchiveHelperEventFilter:
    def test_release_skips_events_outside_filter(self, rf, member, other_user):
        official = make_event(created_by=other_user, event_type=EventType.OFFICIAL)
        community = make_event(created_by=other_user)
        make_rsvp(official, member)
        make_rsvp(community, member)

        release_upcoming_rsvps(rf.get("/"), member, ~KEPT_EVENT_Q)

        assert EventRSVP.objects.get(event=official, user=member).status == RSVPStatus.ATTENDING
        assert EventRSVP.objects.get(event=community, user=member).status == RSVPStatus.CANT_GO

    def test_step_down_skips_events_outside_filter(self, member, other_user):
        official = make_event(created_by=other_user, event_type=EventType.OFFICIAL)
        community = make_event(created_by=other_user)
        official.co_hosts.add(member)
        community.co_hosts.add(member)

        step_down_as_cohost(member, ~KEPT_EVENT_Q)

        assert official.co_hosts.filter(pk=member.pk).exists()
        assert not community.co_hosts.filter(pk=member.pk).exists()
