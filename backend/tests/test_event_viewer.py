import pytest
from community._event_viewer import resolve_event_viewer
from community.models import Event, EventRSVP, RSVPStatus
from users.models import NonMemberRsvpToken, User

from tests.conftest import future_iso


@pytest.fixture
def event(db, test_user):
    return Event.objects.create(
        title="Resolver Test Event",
        start_datetime=future_iso(days=10),
        created_by=test_user,
    )


@pytest.fixture
def other_event(db, test_user):
    return Event.objects.create(
        title="Other Event",
        start_datetime=future_iso(days=11),
        created_by=test_user,
    )


@pytest.fixture
def non_member(db):
    user = User.objects.create_user(
        phone_number="+12025550199",
        first_name="Non",
        last_name="Member",
        email="non@example.com",
        is_member=False,
    )
    user.set_unusable_password()
    user.save(update_fields=["password"])
    return user


def _request(rf, query=""):
    return rf.get(f"/api/community/events/x/?{query}")


@pytest.mark.django_db
class TestResolveEventViewer:
    def test_no_token_no_jwt_returns_none(self, rf, event):
        request = _request(rf)
        request.auth = None
        assert resolve_event_viewer(request, event.id) is None

    def test_real_jwt_user_returned_regardless_of_token(self, rf, event, test_user):
        request = _request(rf)
        request.auth = test_user
        assert resolve_event_viewer(request, event.id) == test_user

    def test_valid_token_with_rsvp_on_this_event_unlocks(self, rf, event, non_member):
        EventRSVP.objects.create(event=event, user=non_member, status=RSVPStatus.ATTENDING)
        token = NonMemberRsvpToken.issue(non_member)
        request = _request(rf, query=f"token={token.token}")
        request.auth = None
        assert resolve_event_viewer(request, event.id) == non_member

    def test_valid_token_without_rsvp_on_this_event_stays_locked(
        self, rf, event, other_event, non_member
    ):
        EventRSVP.objects.create(event=other_event, user=non_member, status=RSVPStatus.ATTENDING)
        token = NonMemberRsvpToken.issue(non_member)
        request = _request(rf, query=f"token={token.token}")
        request.auth = None
        assert resolve_event_viewer(request, event.id) is None

    def test_invalid_token_stays_locked(self, rf, event):
        request = _request(rf, query="token=not-a-real-token")
        request.auth = None
        assert resolve_event_viewer(request, event.id) is None

    def test_expired_token_stays_locked(self, rf, event, non_member):
        EventRSVP.objects.create(event=event, user=non_member, status=RSVPStatus.ATTENDING)
        token = NonMemberRsvpToken.issue(non_member)
        from datetime import timedelta

        from django.utils import timezone

        token.expires_at = timezone.now() - timedelta(days=1)
        token.save(update_fields=["expires_at"])
        request = _request(rf, query=f"token={token.token}")
        request.auth = None
        assert resolve_event_viewer(request, event.id) is None
