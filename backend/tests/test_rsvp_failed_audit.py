import pytest
from audit.models import AuditLogEntry
from community.models import RSVPStatus
from community.validation import Code
from django.utils import timezone

from tests._auth import auth_headers_for
from tests._events import make_event
from tests._public_rsvp_helpers import make_official_event, post
from tests._users import make_user

pytestmark = pytest.mark.django_db


def _rsvp(api_client, event, user, method="post"):
    return getattr(api_client, method)(
        f"/api/community/events/{event.id}/rsvp/",
        {"status": RSVPStatus.ATTENDING},
        content_type="application/json",
        **auth_headers_for(user),
    )


def _failure() -> tuple[str, dict]:
    entry = AuditLogEntry.objects.get(action="rsvp_failed")
    return entry.target_id, entry.details


def test_member_rsvp_to_closed_event_is_audited(api_client, test_user):
    event = make_event(created_by=test_user, rsvp_enabled=True, rsvps_closed_at=timezone.now())
    guest = make_user()

    assert _rsvp(api_client, event, guest).status_code == 400

    assert _failure() == (
        str(event.id),
        {"code": Code.Event.RSVPS_CLOSED_BY_HOST, "user_id": str(guest.pk)},
    )


def test_cancelling_a_missing_rsvp_is_audited(api_client, test_user):
    event = make_event(created_by=test_user, rsvp_enabled=True)

    assert _rsvp(api_client, event, test_user, method="delete").status_code == 404

    assert _failure()[1]["code"] == Code.Event.RSVP_NOT_FOUND


def test_public_rsvp_failure_has_no_member(api_client):
    event = make_official_event(rsvps_closed_at=timezone.now())

    assert post(api_client, event).status_code == 400

    assert _failure() == (str(event.id), {"code": Code.Event.RSVPS_CLOSED_BY_HOST})


def test_successful_rsvp_is_not_a_failure(api_client, test_user):
    event = make_event(created_by=test_user, rsvp_enabled=True)

    assert _rsvp(api_client, event, test_user).status_code == 200

    assert not AuditLogEntry.objects.filter(action="rsvp_failed").exists()
