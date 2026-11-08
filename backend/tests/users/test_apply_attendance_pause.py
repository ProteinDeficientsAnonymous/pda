from datetime import timedelta

import pytest
from audit.models import AuditLogEntry
from community.models import (
    CoHostInviteStatus,
    EventCoHostInvite,
    EventRSVP,
    EventStatus,
    EventType,
    RSVPStatus,
)
from django.utils import timezone
from tests._events import make_event, make_rsvp
from users._attendance_pause import apply_attendance_pause
from users.roles import Role


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
        event = make_event(created_by=other_user, max_attendees=1)
        make_rsvp(event, member)
        waiting = make_rsvp(event, other_user, RSVPStatus.WAITLISTED)

        apply_attendance_pause(rf.get("/"), member)

        rsvp = EventRSVP.objects.get(event=event, user=member)
        assert rsvp.status == RSVPStatus.CANT_GO
        assert rsvp.cancelled_at is not None
        waiting.refresh_from_db()
        assert waiting.status == RSVPStatus.ATTENDING

    @pytest.mark.parametrize("event_type", [EventType.OFFICIAL, EventType.CLUB])
    def test_keeps_official_and_club_rsvp(self, rf, member, other_user, event_type):
        rsvped = make_event(created_by=other_user, event_type=event_type)
        make_rsvp(rsvped, member)

        apply_attendance_pause(rf.get("/"), member)

        assert EventRSVP.objects.get(event=rsvped, user=member).status == RSVPStatus.ATTENDING

    def test_keeps_official_rsvp_when_stepping_down_as_its_cohost(self, rf, member, other_user):
        event = make_event(created_by=other_user, event_type=EventType.OFFICIAL)
        event.co_hosts.add(member)
        make_rsvp(event, member)

        apply_attendance_pause(rf.get("/"), member)

        assert list(event.co_hosts.all()) == [other_user]
        assert EventRSVP.objects.get(event=event, user=member).status == RSVPStatus.ATTENDING

    @pytest.mark.parametrize("event_type", list(EventType))
    def test_steps_down_from_shared_hosting(self, rf, member, other_user, event_type):
        event = make_event(created_by=other_user, event_type=event_type)
        event.co_hosts.add(member)
        EventCoHostInvite.objects.create(
            event=event, user=member, status=CoHostInviteStatus.ACCEPTED
        )

        apply_attendance_pause(rf.get("/"), member)

        assert list(event.co_hosts.all()) == [other_user]
        invite = EventCoHostInvite.objects.get(event=event, user=member)
        assert invite.status == CoHostInviteStatus.REMOVED

    @pytest.mark.parametrize("event_type", list(EventType))
    def test_rescinds_pending_invites(self, rf, member, other_user, event_type):
        event = make_event(created_by=other_user, event_type=event_type)
        invite = EventCoHostInvite.objects.create(event=event, user=member)

        apply_attendance_pause(rf.get("/"), member)

        invite.refresh_from_db()
        assert invite.status == CoHostInviteStatus.RESCINDED

    def test_leaves_pending_invites_on_past_events(self, rf, member, other_user):
        past = make_event(created_by=other_user, start_datetime=timezone.now() - timedelta(days=3))
        EventCoHostInvite.objects.create(event=past, user=member)

        apply_attendance_pause(rf.get("/"), member)

        invite = EventCoHostInvite.objects.get(event=past, user=member)
        assert invite.status == CoHostInviteStatus.PENDING

    @pytest.mark.parametrize("event_type", list(EventType))
    def test_moves_sole_hosted_event_to_draft_without_rsvps(
        self, rf, member, other_user, event_type
    ):
        event = make_event(created_by=member, event_type=event_type)
        make_rsvp(event, member)
        make_rsvp(event, other_user)

        apply_attendance_pause(rf.get("/"), member)

        event.refresh_from_db()
        assert event.status == EventStatus.DRAFT
        assert event.co_hosts.count() == 0
        assert not EventRSVP.objects.filter(event=event).exists()

    def test_writes_audit_log(self, rf, member, other_user, django_capture_on_commit_callbacks):
        vettor = Role.objects.create(name="vettor")
        member.roles.add(vettor)
        drafted = make_event(created_by=member)
        removed = make_event(created_by=other_user)
        make_rsvp(removed, member)
        shared = make_event(created_by=other_user)
        shared.co_hosts.add(member)

        with django_capture_on_commit_callbacks(execute=True):
            apply_attendance_pause(rf.get("/"), member)

        entry = AuditLogEntry.objects.get(action="user_attendance_paused")
        assert entry.target_id == str(member.pk)
        assert entry.details["drafted_event_ids"] == [str(drafted.pk)]
        assert entry.details["removed_rsvp_event_ids"] == [str(removed.pk)]
        assert entry.details["removed_role_ids"] == [str(vettor.pk)]
        assert entry.details["removed_hosting_event_ids"] == [str(shared.pk)]
