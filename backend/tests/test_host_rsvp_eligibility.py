import pytest
from community.models import Event, EventRSVP, EventType, RSVPStatus
from django.utils import timezone
from users.models import MembershipStatus

from tests._asserts import assert_error_code
from tests._auth import auth_headers_for
from tests._time import future_iso
from tests._users import make_attendance_paused, make_user


@pytest.fixture
def host(db):
    return make_user(first_name="Host")


@pytest.fixture
def event(host):
    return Event.objects.create(
        title="Eligibility Event",
        start_datetime=future_iso(days=14),
        end_datetime=future_iso(days=14, hours=2),
        rsvp_enabled=True,
        created_by=host,
    )


def _set_rsvp(api_client, event, host, user):
    return api_client.post(
        f"/api/community/events/{event.id}/rsvps/{user.pk}/rsvp/",
        {"status": RSVPStatus.ATTENDING},
        content_type="application/json",
        **auth_headers_for(host),
    )


@pytest.mark.django_db
class TestHostRsvpEligibility:
    @pytest.mark.parametrize(
        ("status", "archived"),
        [
            (MembershipStatus.ARCHIVED, True),
            (MembershipStatus.GUIDELINES_PAUSED, False),
            (MembershipStatus.NONE, False),
        ],
    )
    def test_refuses_target_who_cannot_sign_in(self, api_client, event, host, status, archived):
        target = make_user(
            membership_status=status, archived_at=timezone.now() if archived else None
        )
        response = _set_rsvp(api_client, event, host, target)
        assert response.status_code == 400
        assert_error_code(response, "event.guest_not_eligible")
        assert not EventRSVP.objects.filter(event=event, user=target).exists()

    @pytest.mark.parametrize(
        "make_target",
        [lambda: make_user(membership_status=MembershipStatus.TENTATIVE), make_attendance_paused],
    )
    def test_allows_limited_target_on_official_event(self, api_client, event, host, make_target):
        event.event_type = EventType.OFFICIAL
        event.save(update_fields=["event_type"])
        target = make_target()
        assert _set_rsvp(api_client, event, host, target).status_code == 200
        assert EventRSVP.objects.filter(event=event, user=target).exists()

    def test_refused_target_keeps_existing_rsvp(self, api_client, event, host):
        target = make_user(membership_status=MembershipStatus.GUIDELINES_PAUSED)
        EventRSVP.objects.create(event=event, user=target, status=RSVPStatus.MAYBE)
        response = _set_rsvp(api_client, event, host, target)
        assert response.status_code == 400
        assert EventRSVP.objects.get(event=event, user=target).status == RSVPStatus.MAYBE
