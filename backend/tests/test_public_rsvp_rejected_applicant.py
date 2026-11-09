import pytest
from community.models import EventRSVP, JoinRequest, JoinRequestStatus, RSVPStatus
from community.validation import Code
from users.models import PublicRsvpToken, User

from tests._public_rsvp_helpers import (
    first_code,
    make_official_event,
    make_public_rsvper,
    payload,
    post,
)

pytestmark = pytest.mark.django_db

PHONE = payload()["phone_number"]


@pytest.fixture
def official_event(db):
    return make_official_event()


def _join_request(status, **extra):
    return JoinRequest.objects.create(
        first_name="Sam", phone_number=PHONE, email="sam@example.com", status=status, **extra
    )


def test_rejected_applicant_without_account_cannot_rsvp(
    api_client, official_event, fake_email_sender
):
    _join_request(JoinRequestStatus.REJECTED)
    response = post(api_client, official_event)
    assert response.status_code == 409
    assert first_code(response) == Code.Event.RSVP_COULD_NOT_BE_CREATED
    assert not User.objects.filter(phone_number=PHONE).exists()
    fake_email_sender.send.assert_not_called()


def test_rejected_public_rsvper_cannot_rsvp(api_client, official_event):
    rsvper = make_public_rsvper(PHONE, "sam@example.com")
    _join_request(JoinRequestStatus.REJECTED, user=rsvper)
    response = post(api_client, official_event)
    assert response.status_code == 409
    assert not EventRSVP.objects.filter(user=rsvper).exists()


def test_reapplied_applicant_can_rsvp(api_client, official_event, fake_email_sender):
    _join_request(JoinRequestStatus.REJECTED)
    _join_request(JoinRequestStatus.PENDING)
    response = post(api_client, official_event)
    assert response.status_code == 200


def test_rejected_applicant_cannot_rsvp_with_manage_link(api_client, official_event):
    rsvper = make_public_rsvper(PHONE, "sam@example.com")
    token = PublicRsvpToken.issue_or_extend(rsvper)
    _join_request(JoinRequestStatus.REJECTED, user=rsvper)
    response = api_client.post(
        f"/api/community/public/my-rsvps/{official_event.id}/?token={token.token}",
        {"status": RSVPStatus.ATTENDING},
        content_type="application/json",
    )
    assert response.status_code == 409
    assert first_code(response) == Code.Event.RSVP_COULD_NOT_BE_CREATED
    assert not EventRSVP.objects.filter(user=rsvper).exists()
