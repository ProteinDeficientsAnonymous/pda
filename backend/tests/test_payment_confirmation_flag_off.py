import pytest
from community.models import (
    Event,
    EventRSVP,
    FeatureFlag,
    FeatureFlagState,
    RSVPStatus,
    resolve_flags,
)

from tests._public_rsvp_helpers import make_official_event, post, url
from tests.conftest import future_iso

FLAG = FeatureFlag.EVENT_PAYMENT_CONFIRMATION


def disable_flag():
    FeatureFlagState.objects.update_or_create(key=FLAG, defaults={"enabled": False})


@pytest.fixture
def paid_event(db, test_user):
    return Event.objects.create(
        title="Paid Event",
        start_datetime=future_iso(days=30),
        end_datetime=future_iso(days=30, hours=2),
        rsvp_enabled=True,
        created_by=test_user,
        price="$10",
        venmo_link="https://venmo.com/host",
    )


@pytest.mark.django_db
class TestFlagRegistered:
    def test_flag_defaults_off(self):
        assert resolve_flags()[FLAG] is False


@pytest.mark.django_db
class TestMemberPathFlagOff:
    def test_default_off_attending_paid_succeeds_without_confirmation(
        self, api_client, auth_headers, paid_event, test_user
    ):
        response = api_client.post(
            f"/api/community/events/{paid_event.id}/rsvp/",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["my_rsvp"] == RSVPStatus.ATTENDING
        assert EventRSVP.objects.filter(
            event=paid_event, user=test_user, status=RSVPStatus.ATTENDING
        ).exists()

    def test_explicitly_off_attending_paid_succeeds_without_confirmation(
        self, api_client, auth_headers, paid_event, test_user
    ):
        disable_flag()
        response = api_client.post(
            f"/api/community/events/{paid_event.id}/rsvp/",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["my_rsvp"] == RSVPStatus.ATTENDING


@pytest.mark.django_db
class TestPublicPathFlagOff:
    def _paid_official_event(self):
        return make_official_event(price="$10", venmo_link="https://venmo.com/host")

    def test_default_off_new_person_attending_paid_succeeds(self, api_client, fake_email_sender):
        event = self._paid_official_event()
        response = post(api_client, event, status=RSVPStatus.ATTENDING)
        assert response.status_code == 200

    def test_explicitly_off_new_person_attending_paid_succeeds(self, api_client, fake_email_sender):
        disable_flag()
        event = self._paid_official_event()
        response = api_client.post(
            url(event),
            {
                "first_name": "Sam",
                "last_name": "Green",
                "email": "sam@example.com",
                "phone_number": "+14155550123",
                "status": RSVPStatus.ATTENDING,
                "has_plus_one": False,
            },
            content_type="application/json",
        )
        assert response.status_code == 200
