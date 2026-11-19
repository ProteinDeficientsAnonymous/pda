import pytest
from community.models import JoinRequestStatus

from tests._tentative_helpers import check_in, open_official_event, tentative_user_with_rsvp

__all__ = ["open_official_event"]

pytestmark = pytest.mark.django_db


@pytest.fixture
def checked_in_tentative(
    api_client, sample_join_request, vettor_user, open_official_event, fake_email_sender
):
    user = tentative_user_with_rsvp(sample_join_request, open_official_event, vettor_user)
    check_in(api_client, open_official_event, user)
    sample_join_request.refresh_from_db()
    return sample_join_request, open_official_event


def test_check_in_promotion_records_the_event(checked_in_tentative):
    join_request, event = checked_in_tentative
    assert join_request.status == JoinRequestStatus.APPROVED
    assert join_request.approved_via_event == event


def test_list_exposes_the_approving_event(api_client, vettor_headers, checked_in_tentative):
    join_request, event = checked_in_tentative
    response = api_client.get("/api/community/join-requests/", **vettor_headers)
    row = next(r for r in response.json() if r["id"] == str(join_request.id))
    assert row["approved_via_event_id"] == str(event.id)
    assert row["approved_via_event_title"] == "Official Meetup"


def test_manual_approval_records_no_event(api_client, vettor_headers, sample_join_request):
    api_client.patch(
        f"/api/community/join-requests/{sample_join_request.id}/",
        {"status": JoinRequestStatus.APPROVED},
        content_type="application/json",
        **vettor_headers,
    )
    response = api_client.get("/api/community/join-requests/", **vettor_headers)
    row = next(r for r in response.json() if r["id"] == str(sample_join_request.id))
    assert row["approved_via_event_id"] is None
    assert row["approved_via_event_title"] is None
