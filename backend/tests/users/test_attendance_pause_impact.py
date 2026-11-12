from datetime import timedelta

import pytest
from community.models import EventRSVP, EventStatus, EventType, RSVPStatus
from django.utils import timezone
from tests._events import make_event, make_rsvp
from users._archive import release_upcoming_rsvps
from users._attendance_pause import KEPT_RSVP_EVENT_Q, pause_impact
from users.models import MembershipStatus


def _in_days(days: int):
    return timezone.now() + timedelta(days=days)


@pytest.mark.django_db
class TestAttendancePauseImpact:
    @pytest.mark.parametrize("event_type", [EventType.OFFICIAL, EventType.CLUB])
    def test_keeps_official_and_club_rsvps(self, member, other_user, event_type):
        event = make_event(created_by=other_user, event_type=event_type)
        make_rsvp(event, member)
        assert pause_impact(member, MembershipStatus.ATTENDANCE_PAUSED).kept_rsvps == [event]

    @pytest.mark.parametrize(
        "status", [RSVPStatus.ATTENDING, RSVPStatus.MAYBE, RSVPStatus.WAITLISTED]
    )
    def test_removes_other_rsvps(self, member, other_user, status):
        event = make_event(created_by=other_user)
        make_rsvp(event, member, status)
        assert pause_impact(member, MembershipStatus.ATTENDANCE_PAUSED).removed_rsvps == [event]

    def test_ignores_cant_go_rsvps(self, member, other_user):
        make_rsvp(make_event(created_by=other_user), member, RSVPStatus.CANT_GO)
        assert pause_impact(member, MembershipStatus.ATTENDANCE_PAUSED).removed_rsvps == []

    @pytest.mark.parametrize("event_type", list(EventType))
    def test_removes_shared_hosting(self, member, other_user, event_type):
        event = make_event(created_by=other_user, event_type=event_type)
        event.co_hosts.add(member)
        assert pause_impact(member, MembershipStatus.ATTENDANCE_PAUSED).removed_hosting == [event]

    @pytest.mark.parametrize("event_type", list(EventType))
    def test_drafts_sole_hosted_events(self, member, event_type):
        event = make_event(created_by=member, event_type=event_type)
        assert pause_impact(member, MembershipStatus.ATTENDANCE_PAUSED).drafted_events == [event]

    def test_drafted_event_rsvp_is_not_listed_as_removed(self, member):
        event = make_event(created_by=member)
        make_rsvp(event, member)
        impact = pause_impact(member, MembershipStatus.ATTENDANCE_PAUSED)
        assert impact.drafted_events == [event]
        assert impact.removed_rsvps == []

    def test_excludes_past_events(self, member, other_user):
        make_rsvp(make_event(created_by=other_user, start_datetime=_in_days(-3)), member)
        make_event(created_by=member, start_datetime=_in_days(-3))
        impact = pause_impact(member, MembershipStatus.ATTENDANCE_PAUSED)
        assert impact.removed_rsvps == []
        assert impact.drafted_events == []

    def test_excludes_cancelled_events(self, member, other_user):
        make_rsvp(make_event(created_by=other_user, status=EventStatus.CANCELLED), member)
        assert pause_impact(member, MembershipStatus.ATTENDANCE_PAUSED).removed_rsvps == []

    def test_orders_soonest_first(self, member, other_user):
        later = make_event(created_by=other_user, start_datetime=_in_days(9))
        sooner = make_event(created_by=other_user, start_datetime=_in_days(2))
        make_rsvp(later, member)
        make_rsvp(sooner, member)
        assert pause_impact(member, MembershipStatus.ATTENDANCE_PAUSED).removed_rsvps == [
            sooner,
            later,
        ]


@pytest.mark.django_db
class TestArchiveHelperEventFilter:
    def test_release_skips_events_outside_filter(self, rf, member, other_user):
        official = make_event(created_by=other_user, event_type=EventType.OFFICIAL)
        community = make_event(created_by=other_user)
        make_rsvp(official, member)
        make_rsvp(community, member)

        release_upcoming_rsvps(rf.get("/"), member, ~KEPT_RSVP_EVENT_Q)

        assert EventRSVP.objects.get(event=official, user=member).status == RSVPStatus.ATTENDING
        assert EventRSVP.objects.get(event=community, user=member).status == RSVPStatus.CANT_GO
