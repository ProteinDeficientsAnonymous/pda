import pytest
from users.models import MembershipStatus, User

from tests._public_rsvp_helpers import make_official_event, post

pytestmark = pytest.mark.django_db

NEW_PHONE = "+12025550777"


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        (
            "/api/auth/create-user/",
            {"phone_number": NEW_PHONE, "first_name": "New", "email": "new@example.com"},
        ),
        ("/api/auth/bulk-create-users/", {"phone_numbers": [NEW_PHONE]}),
    ],
    ids=["single", "bulk"],
)
def test_admin_create_records_the_creator(
    api_client, manage_users_user, manage_users_headers, path, payload
):
    response = api_client.post(
        path, payload, content_type="application/json", **manage_users_headers
    )
    assert response.status_code in (200, 201)
    created = User.objects.get(phone_number=NEW_PHONE)
    assert created.membership_status_changed_by == manage_users_user
    assert created.membership_status_changed_at is not None


def test_public_rsvp_stamps_no_actor(api_client):
    assert post(api_client, make_official_event()).status_code in (200, 201)
    rsvper = User.objects.get(membership_status=MembershipStatus.NONE)
    assert rsvper.membership_status_changed_at is not None
    assert rsvper.membership_status_changed_by is None
