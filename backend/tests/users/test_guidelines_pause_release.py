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
from tests._events import make_event, make_rsvp
from users.roles import Role


@pytest.fixture
def set_pause(api_client, manage_users_headers, django_capture_on_commit_callbacks):
    def patch(user, paused: bool, field: str = "is_paused"):
        with django_capture_on_commit_callbacks(execute=True):
            response = api_client.patch(
                f"/api/auth/users/{user.pk}/",
                {field: paused},
                content_type="application/json",
                **manage_users_headers,
            )
        assert response.status_code == 200
        user.refresh_from_db()

    return patch


@pytest.mark.django_db
class TestGuidelinesPauseRelease:
    @pytest.mark.parametrize("event_type", list(EventType))
    def test_releases_every_rsvp(self, set_pause, member, other_user, event_type):
        event = make_event(created_by=other_user, event_type=event_type)
        make_rsvp(event, member)

        set_pause(member, True)

        assert EventRSVP.objects.get(event=event, user=member).status == RSVPStatus.CANT_GO

    def test_releases_rsvps_an_attendance_pause_kept(self, set_pause, member, other_user):
        official = make_event(created_by=other_user, event_type=EventType.OFFICIAL)
        make_rsvp(official, member)
        set_pause(member, True, field="attendance_paused")
        assert EventRSVP.objects.get(event=official, user=member).status == RSVPStatus.ATTENDING

        set_pause(member, True)

        assert EventRSVP.objects.get(event=official, user=member).status == RSVPStatus.CANT_GO

    def test_releases_hosting_and_audits_it(self, set_pause, member, other_user):
        vettor = Role.objects.create(name="vettor")
        member.roles.add(vettor)
        drafted = make_event(created_by=member, event_type=EventType.OFFICIAL)
        official = make_event(created_by=other_user, event_type=EventType.OFFICIAL)
        make_rsvp(official, member)
        shared = make_event(created_by=other_user)
        shared.co_hosts.add(member)
        invite = EventCoHostInvite.objects.create(event=official, user=member)

        set_pause(member, True)

        drafted.refresh_from_db()
        assert drafted.status == EventStatus.DRAFT
        assert list(shared.co_hosts.all()) == [other_user]
        invite.refresh_from_db()
        assert invite.status == CoHostInviteStatus.RESCINDED
        assert list(member.roles.all()) == []
        entry = AuditLogEntry.objects.get(action="user_paused")
        assert entry.details == {
            "removed_role_ids": [str(vettor.pk)],
            "removed_rsvp_event_ids": [str(official.pk)],
            "removed_hosting_event_ids": [str(shared.pk)],
            "drafted_event_ids": [str(drafted.pk)],
        }
