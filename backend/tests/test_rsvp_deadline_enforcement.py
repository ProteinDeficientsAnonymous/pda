from datetime import timedelta

import pytest
from community.models import Event, EventRSVP, RSVPStatus
from community.validation import Code
from django.utils import timezone
from users.models import PublicRsvpToken

from tests._asserts import assert_error_code
from tests._auth import auth_headers_for
from tests._public_rsvp_helpers import make_official_event, make_public_rsvper
from tests._time import future_iso
from tests._users import make_user


def _rsvp_url(event: Event) -> str:
    return f"/api/community/events/{event.id}/rsvp/"


@pytest.fixture
def guest(db):
    return make_user()


def _event(host, deadline_in: timedelta | None) -> Event:
    return Event.objects.create(
        title="Deadline Event",
        start_datetime=future_iso(days=7),
        rsvp_enabled=True,
        rsvp_deadline=None if deadline_in is None else timezone.now() + deadline_in,
        created_by=host,
    )


@pytest.fixture
def closed_event(test_user):
    return _event(test_user, timedelta(hours=-1))


def _post_rsvp(api_client, event, user, status):
    return api_client.post(
        _rsvp_url(event),
        {"status": status},
        content_type="application/json",
        **auth_headers_for(user),
    )


@pytest.mark.django_db
class TestMemberDeadline:
    def test_open_deadline_allows_any_rsvp(self, api_client, test_user, guest):
        event = _event(test_user, timedelta(days=1))
        assert _post_rsvp(api_client, event, guest, RSVPStatus.MAYBE).status_code == 200

    def test_no_deadline_behaves_as_before(self, api_client, test_user, guest):
        event = _event(test_user, None)
        EventRSVP.objects.create(event=event, user=guest, status=RSVPStatus.CANT_GO)
        assert _post_rsvp(api_client, event, guest, RSVPStatus.MAYBE).status_code == 200

    def test_new_rsvp_rejected(self, api_client, closed_event, guest):
        response = _post_rsvp(api_client, closed_event, guest, RSVPStatus.ATTENDING)
        assert response.status_code == 400
        assert_error_code(response, Code.Event.RSVPS_CLOSED_DEADLINE)
        assert not EventRSVP.objects.filter(event=closed_event).exists()

    @pytest.mark.parametrize(
        ("current", "requested"),
        [
            (RSVPStatus.MAYBE, RSVPStatus.ATTENDING),
            (RSVPStatus.MAYBE, RSVPStatus.CANT_GO),
            (RSVPStatus.CANT_GO, RSVPStatus.ATTENDING),
            (RSVPStatus.ATTENDING, RSVPStatus.MAYBE),
        ],
    )
    def test_status_change_rejected(self, api_client, closed_event, guest, current, requested):
        EventRSVP.objects.create(event=closed_event, user=guest, status=current)
        response = _post_rsvp(api_client, closed_event, guest, requested)
        assert response.status_code == 400
        assert_error_code(response, Code.Event.RSVPS_CLOSED_DEADLINE)
        assert EventRSVP.objects.get(event=closed_event, user=guest).status == current

    @pytest.mark.parametrize("current", [RSVPStatus.ATTENDING, RSVPStatus.WAITLISTED])
    def test_going_can_switch_to_cant_go(self, api_client, closed_event, guest, current):
        EventRSVP.objects.create(event=closed_event, user=guest, status=current)
        response = _post_rsvp(api_client, closed_event, guest, RSVPStatus.CANT_GO)
        assert response.status_code == 200
        assert EventRSVP.objects.get(event=closed_event, user=guest).status == RSVPStatus.CANT_GO

    def test_host_is_exempt(self, api_client, closed_event, test_user):
        response = _post_rsvp(api_client, closed_event, test_user, RSVPStatus.ATTENDING)
        assert response.status_code == 200

    def test_delete_rejected_for_maybe(self, api_client, closed_event, guest):
        EventRSVP.objects.create(event=closed_event, user=guest, status=RSVPStatus.MAYBE)
        response = api_client.delete(_rsvp_url(closed_event), **auth_headers_for(guest))
        assert response.status_code == 400
        assert_error_code(response, Code.Event.RSVPS_CLOSED_DEADLINE)
        assert EventRSVP.objects.filter(event=closed_event, user=guest).exists()

    def test_delete_allowed_for_going(self, api_client, closed_event, guest):
        EventRSVP.objects.create(event=closed_event, user=guest, status=RSVPStatus.ATTENDING)
        response = api_client.delete(_rsvp_url(closed_event), **auth_headers_for(guest))
        assert response.status_code == 204


@pytest.mark.django_db
class TestPublicDeadline:
    @pytest.fixture
    def rsvper(self):
        return make_public_rsvper("+14155550441", "deadline@example.com")

    @pytest.fixture
    def event(self):
        return make_official_event(rsvp_deadline=timezone.now() - timedelta(hours=1))

    def _manage_url(self, event, rsvper) -> str:
        token = PublicRsvpToken.issue_or_extend(rsvper)
        return f"/api/community/public/my-rsvps/{event.id}/?token={token.token}"

    def test_maybe_cannot_confirm(self, api_client, event, rsvper):
        EventRSVP.objects.create(event=event, user=rsvper, status=RSVPStatus.MAYBE)
        response = api_client.post(
            self._manage_url(event, rsvper),
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Event.RSVPS_CLOSED_DEADLINE)

    def test_maybe_cannot_delete(self, api_client, event, rsvper):
        EventRSVP.objects.create(event=event, user=rsvper, status=RSVPStatus.MAYBE)
        response = api_client.delete(self._manage_url(event, rsvper))
        assert response.status_code == 400
        assert EventRSVP.objects.filter(event=event, user=rsvper).exists()

    def test_going_can_delete(self, api_client, event, rsvper):
        EventRSVP.objects.create(event=event, user=rsvper, status=RSVPStatus.ATTENDING)
        response = api_client.delete(self._manage_url(event, rsvper))
        assert response.status_code == 204
