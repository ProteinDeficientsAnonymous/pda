import json

import pytest
from community.models import EventStatus
from tests._auth import auth_headers_for
from tests._events import make_event
from tests._users import make_user
from users._attendance_pause import apply_attendance_pause
from users.models import MembershipStatus

URL = "/api/community/events/"


@pytest.fixture
def drafted(rf, member):
    event = make_event(title="Potluck", location="the park", created_by=member)
    apply_attendance_pause(rf.get("/"), member)
    event.refresh_from_db()
    assert event.status == EventStatus.DRAFT
    return event


def _restore(user):
    user.save(update_fields=user.set_membership_status(MembershipStatus.ACTIVE_MEMBER, by=None))


def _listed_draft_ids(api_client, user) -> set[str]:
    response = api_client.get(f"{URL}?status=draft", **auth_headers_for(user))
    return {e["id"] for e in response.json()}


@pytest.mark.django_db
@pytest.mark.parametrize("restored", [False, True])
class TestPauseDraftedCreator:
    def test_opens_the_draft_it_lists(self, api_client, member, drafted, restored):
        if restored:
            _restore(member)

        assert str(drafted.id) in _listed_draft_ids(api_client, member)
        response = api_client.get(f"{URL}{drafted.id}/", **auth_headers_for(member))
        assert response.status_code == 200
        assert response.json()["location"] == "the park"

    def test_cannot_publish(self, api_client, member, drafted, restored):
        if restored:
            _restore(member)

        response = api_client.patch(
            f"{URL}{drafted.id}/",
            data=json.dumps({"status": EventStatus.ACTIVE}),
            content_type="application/json",
            **auth_headers_for(member),
        )
        assert response.status_code == 403
        drafted.refresh_from_db()
        assert drafted.status == EventStatus.DRAFT


@pytest.mark.django_db
def test_other_member_neither_lists_nor_opens(api_client, drafted):
    other = make_user(phone_number="+12025550499")

    assert str(drafted.id) not in _listed_draft_ids(api_client, other)
    response = api_client.get(f"{URL}{drafted.id}/", **auth_headers_for(other))
    assert response.status_code == 403
