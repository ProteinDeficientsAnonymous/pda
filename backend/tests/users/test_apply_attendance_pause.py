from datetime import timedelta

import pytest
from audit.models import AuditLogEntry
from community.models import (
    CoHostInviteStatus,
    Event,
    EventCoHostInvite,
    EventRSVP,
    EventStatus,
    EventType,
    RSVPStatus,
)
from django.utils import timezone
from users._attendance_pause import apply_attendance_pause
from users.models import User
from users.roles import Role


def _event(creator: User, event_type=EventType.COMMUNITY, **extra) -> Event:
    return Event.objects.create(
        title="potluck",
        event_type=event_type,
        start_datetime=timezone.now() + timedelta(days=3),
        created_by=creator,
        status=EventStatus.ACTIVE,
        **extra,
    )


def _rsvp(event: Event, user: User, status=RSVPStatus.ATTENDING) -> EventRSVP:
    return EventRSVP.objects.create(event=event, user=user, status=status)


@pytest.mark.django_db
class TestApplyAttendancePause:
    def test_sets_pause_fields(self, rf, member):
        member.has_joined_whatsapp = True
        member.save(update_fields=["has_joined_whatsapp"])

        apply_attendance_pause(rf.get("/"), member)

        member.refresh_from_db()
        assert member.attendance_paused_at is not None
        assert member.is_member is False
        assert member.has_joined_whatsapp is False
        assert member.is_paused is False

    def test_strips_every_role(self, rf, member):
        member_role, _ = Role.objects.get_or_create(name="member", is_default=True)
        vettor = Role.objects.create(name="vettor")
        member.roles.add(member_role, vettor)

        apply_attendance_pause(rf.get("/"), member)

        assert member.roles.count() == 0

    def test_removes_other_rsvp_and_promotes_waitlist(self, rf, member, other_user):
        event = _event(other_user, max_attendees=1)
        _rsvp(event, member)
        waiting = _rsvp(event, other_user, RSVPStatus.WAITLISTED)

        apply_attendance_pause(rf.get("/"), member)

        rsvp = EventRSVP.objects.get(event=event, user=member)
        assert rsvp.status == RSVPStatus.CANT_GO
        assert rsvp.cancelled_at is not None
        waiting.refresh_from_db()
        assert waiting.status == RSVPStatus.ATTENDING

    @pytest.mark.parametrize("event_type", [EventType.OFFICIAL, EventType.CLUB])
    def test_leaves_qualifying_rsvp_and_hosting(self, rf, member, other_user, event_type):
        rsvped = _event(other_user, event_type)
        _rsvp(rsvped, member)
        hosted = _event(member, event_type)

        apply_attendance_pause(rf.get("/"), member)

        assert EventRSVP.objects.get(event=rsvped, user=member).status == RSVPStatus.ATTENDING
        hosted.refresh_from_db()
        assert hosted.status == EventStatus.ACTIVE
        assert list(hosted.co_hosts.all()) == [member]

    def test_steps_down_from_shared_hosting(self, rf, member, other_user):
        event = _event(other_user)
        event.co_hosts.add(member)
        EventCoHostInvite.objects.create(
            event=event, user=member, status=CoHostInviteStatus.ACCEPTED
        )

        apply_attendance_pause(rf.get("/"), member)

        assert list(event.co_hosts.all()) == [other_user]
        invite = EventCoHostInvite.objects.get(event=event, user=member)
        assert invite.status == CoHostInviteStatus.REMOVED

    def test_rescinds_pending_invites_on_other_events_only(self, rf, member, other_user):
        community = _event(other_user)
        official = _event(other_user, EventType.OFFICIAL)
        for event in (community, official):
            EventCoHostInvite.objects.create(event=event, user=member)

        apply_attendance_pause(rf.get("/"), member)

        statuses = dict(
            EventCoHostInvite.objects.filter(user=member).values_list("event_id", "status")
        )
        assert statuses[community.pk] == CoHostInviteStatus.RESCINDED
        assert statuses[official.pk] == CoHostInviteStatus.PENDING

    def test_moves_sole_hosted_event_to_draft_without_rsvps(self, rf, member, other_user):
        event = _event(member)
        _rsvp(event, member)
        _rsvp(event, other_user)

        apply_attendance_pause(rf.get("/"), member)

        event.refresh_from_db()
        assert event.status == EventStatus.DRAFT
        assert event.co_hosts.count() == 0
        assert not EventRSVP.objects.filter(event=event).exists()

    def test_writes_audit_log(self, rf, member, other_user, django_capture_on_commit_callbacks):
        drafted = _event(member)
        removed = _event(other_user)
        _rsvp(removed, member)

        with django_capture_on_commit_callbacks(execute=True):
            apply_attendance_pause(rf.get("/"), member)

        entry = AuditLogEntry.objects.get(action="user_attendance_paused")
        assert entry.target_id == str(member.pk)
        assert entry.details["drafted_event_ids"] == [str(drafted.pk)]
        assert entry.details["removed_rsvp_event_ids"] == [str(removed.pk)]
