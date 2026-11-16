from datetime import timedelta

import pytest
from community.models import (
    CancelReason,
    CoHostInviteStatus,
    Event,
    EventCoHostInvite,
    EventRSVP,
    EventStatus,
    EventType,
    RSVPStatus,
)
from django.utils import timezone
from notifications.models import Notification, NotificationType
from users._archive_user import archive_user
from users.models import User
from users.roles import Role


def _event(creator: User, *, days: int = 3, **extra) -> Event:
    return Event.objects.create(
        title="potluck",
        start_datetime=timezone.now() + timedelta(days=days),
        created_by=creator,
        **extra,
    )


@pytest.mark.django_db
class TestArchiveUser:
    def test_sets_archived_and_clears_calendar_token(self, rf, member):
        member.calendar_token = "tok"
        member.save(update_fields=["calendar_token"])
        archive_user(rf.get("/"), member)
        member.refresh_from_db()
        assert member.archived_at is not None
        assert member.calendar_token == ""

    def test_strips_elevated_roles_and_keeps_member(self, rf, member):
        member_role, _ = Role.objects.get_or_create(name="member", is_default=True)
        vettor = Role.objects.create(name="vettor")
        member.roles.add(member_role, vettor)
        assert archive_user(rf.get("/"), member) == [str(vettor.pk)]
        assert list(member.roles.all()) == [member_role]

    def test_releases_upcoming_rsvp_and_promotes_waitlist(self, rf, member, other_user):
        event = _event(other_user, max_attendees=1)
        EventRSVP.objects.create(event=event, user=member, status=RSVPStatus.ATTENDING)
        waiting = EventRSVP.objects.create(
            event=event, user=other_user, status=RSVPStatus.WAITLISTED
        )
        archive_user(rf.get("/"), member)
        rsvp = EventRSVP.objects.get(event=event, user=member)
        assert rsvp.status == RSVPStatus.CANT_GO
        assert rsvp.cancelled_at is not None
        assert rsvp.cancel_reason == CancelReason.ARCHIVE
        waiting.refresh_from_db()
        assert waiting.status == RSVPStatus.ATTENDING

    def test_emails_promoted_member(
        self, rf, member, other_user, fake_email_sender, django_capture_on_commit_callbacks
    ):
        other_user.email = "other@e.com"
        other_user.save(update_fields=["email"])
        event = _event(other_user, max_attendees=1)
        EventRSVP.objects.create(event=event, user=member, status=RSVPStatus.ATTENDING)
        EventRSVP.objects.create(event=event, user=other_user, status=RSVPStatus.WAITLISTED)

        with django_capture_on_commit_callbacks(execute=True):
            archive_user(rf.get("/"), member)

        sent = fake_email_sender.send.call_args.kwargs
        assert sent["to"] == "other@e.com"
        assert sent["subject"] == "you're off the waitlist for potluck"
        assert "/my-rsvps" not in sent["text"]

    @pytest.mark.parametrize("status", [RSVPStatus.MAYBE, RSVPStatus.WAITLISTED])
    def test_releases_non_attending_holds(self, rf, member, other_user, status):
        event = _event(other_user)
        EventRSVP.objects.create(event=event, user=member, status=status)
        archive_user(rf.get("/"), member)
        assert EventRSVP.objects.get(event=event, user=member).status == RSVPStatus.CANT_GO

    def test_leaves_past_rsvps_alone(self, rf, member, other_user):
        event = _event(other_user, days=-3)
        EventRSVP.objects.create(event=event, user=member, status=RSVPStatus.ATTENDING)
        archive_user(rf.get("/"), member)
        assert EventRSVP.objects.get(event=event, user=member).status == RSVPStatus.ATTENDING

    def test_steps_down_from_shared_upcoming_events(self, rf, member, other_user):
        shared = _event(other_user)
        shared.co_hosts.add(member)
        archive_user(rf.get("/"), member)
        assert list(shared.co_hosts.all()) == [other_user]

    def test_releases_official_rsvp_too(self, rf, member, other_user):
        event = _event(other_user, event_type=EventType.OFFICIAL)
        EventRSVP.objects.create(event=event, user=member, status=RSVPStatus.ATTENDING)
        archive_user(rf.get("/"), member)
        rsvp = EventRSVP.objects.get(event=event, user=member)
        assert rsvp.status == RSVPStatus.CANT_GO
        assert rsvp.cancel_reason == CancelReason.ARCHIVE

    def test_drafts_sole_hosted_event_and_tells_guests(
        self, rf, member, other_user, django_capture_on_commit_callbacks
    ):
        solo = _event(member)
        EventRSVP.objects.create(event=solo, user=other_user, status=RSVPStatus.ATTENDING)
        with django_capture_on_commit_callbacks(execute=True):
            archive_user(rf.get("/"), member)
        solo.refresh_from_db()
        assert solo.status == EventStatus.DRAFT
        assert not solo.co_hosts.exists()
        notice = Notification.objects.get(notification_type=NotificationType.EVENT_UNPUBLISHED)
        assert (notice.recipient, notice.event) == (other_user, solo)

    def test_rescinds_pending_cohost_invites(self, rf, member, other_user):
        upcoming = EventCoHostInvite.objects.create(event=_event(other_user), user=member)
        past = EventCoHostInvite.objects.create(event=_event(other_user, days=-3), user=member)
        archive_user(rf.get("/"), member)
        upcoming.refresh_from_db()
        past.refresh_from_db()
        assert upcoming.status == CoHostInviteStatus.RESCINDED
        assert past.status == CoHostInviteStatus.PENDING


@pytest.mark.django_db
def test_admin_archive_strips_roles(api_client, manage_users_headers, member):
    vettor = Role.objects.create(name="vettor")
    member.roles.add(vettor)
    response = api_client.delete(f"/api/auth/users/{member.pk}/", **manage_users_headers)
    assert response.status_code == 204
    assert not member.roles.filter(pk=vettor.pk).exists()
