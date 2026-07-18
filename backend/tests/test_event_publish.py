import json

import pytest
from community._validation import Code
from community.models import Event, EventStatus
from ninja_jwt.tokens import RefreshToken
from notifications.models import Notification
from users.models import User

from tests._asserts import assert_error_code
from tests.conftest import future_iso, past_iso


@pytest.fixture
def creator(db):
    return User.objects.create_user(
        phone_number="+14155550201",
        password="creatorpass123",
        first_name="Draft",
        last_name="Creator",
    )


@pytest.fixture
def creator_headers(creator):
    refresh = RefreshToken.for_user(creator)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def other_member(db):
    return User.objects.create_user(
        phone_number="+14155550202",
        password="otherpass123",
        first_name="Other",
        last_name="Member",
    )


@pytest.fixture
def other_headers(other_member):
    refresh = RefreshToken.for_user(other_member)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def cohost(db):
    return User.objects.create_user(
        phone_number="+14155550203",
        password="cohostpass123",
        first_name="Draft",
        last_name="Cohost",
    )


@pytest.fixture
def cohost_headers(cohost):
    refresh = RefreshToken.for_user(cohost)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def invitee(db):
    return User.objects.create_user(
        phone_number="+14155550204",
        password="inviteepass123",
        first_name="Draft",
        last_name="Invitee",
    )


@pytest.fixture
def sample_draft(db, creator):
    return Event.objects.create(
        title="Draft BBQ",
        start_datetime=future_iso(days=180),
        created_by=creator,
        status=EventStatus.DRAFT,
    )


@pytest.fixture
def future_active_event(db, creator):
    return Event.objects.create(
        title="Active BBQ",
        start_datetime=future_iso(days=180),
        created_by=creator,
        status=EventStatus.ACTIVE,
    )


@pytest.mark.django_db
class TestPublishDraft:
    def test_publish_draft_transitions_to_active(self, api_client, sample_draft, creator_headers):
        response = api_client.patch(
            f"/api/community/events/{sample_draft.id}/",
            data=json.dumps({"status": "active"}),
            content_type="application/json",
            **creator_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "active"
        sample_draft.refresh_from_db()
        assert sample_draft.status == EventStatus.ACTIVE

    def test_publish_draft_fires_invitee_notifications(
        self, api_client, sample_draft, creator_headers, invitee
    ):
        sample_draft.invited_users.add(invitee)
        response = api_client.patch(
            f"/api/community/events/{sample_draft.id}/",
            data=json.dumps({"status": "active"}),
            content_type="application/json",
            **creator_headers,
        )
        assert response.status_code == 200
        assert Notification.objects.filter(recipient=invitee).exists()

    def test_publish_draft_past_start_rejected(self, api_client, creator_headers, creator):
        draft = Event.objects.create(
            title="Past Draft",
            start_datetime=past_iso(days=90),
            created_by=creator,
            status=EventStatus.DRAFT,
        )
        response = api_client.patch(
            f"/api/community/events/{draft.id}/",
            data=json.dumps({"status": "active"}),
            content_type="application/json",
            **creator_headers,
        )
        assert response.status_code == 400

    def test_publish_stale_draft_with_corrected_date_in_one_patch(
        self, api_client, creator_headers, creator
    ):
        # Fixing a stale draft's past date and publishing in the same PATCH must
        # validate against the new date, not the old one.
        draft = Event.objects.create(
            title="Stale Draft",
            start_datetime=past_iso(days=90),
            created_by=creator,
            status=EventStatus.DRAFT,
        )
        response = api_client.patch(
            f"/api/community/events/{draft.id}/",
            data=json.dumps({"status": "active", "start_datetime": future_iso(days=30)}),
            content_type="application/json",
            **creator_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "active"
        draft.refresh_from_db()
        assert draft.status == EventStatus.ACTIVE

    def test_field_edit_rolls_back_when_status_transition_fails(
        self, api_client, creator_headers, creator
    ):
        draft = Event.objects.create(
            title="Stale Draft",
            start_datetime=past_iso(days=90),
            created_by=creator,
            status=EventStatus.DRAFT,
        )
        response = api_client.patch(
            f"/api/community/events/{draft.id}/",
            data=json.dumps({"title": "new title", "status": "active"}),
            content_type="application/json",
            **creator_headers,
        )
        assert response.status_code == 422
        draft.refresh_from_db()
        assert draft.title == "Stale Draft"
        assert draft.status == EventStatus.DRAFT

    def test_publish_dateless_draft_rejected(self, api_client, creator_headers, creator):
        """A draft with no start_datetime and datetime_tbd=False can't be published.
        Drafts may be saved incomplete, but publishing requires a real date or tbd."""
        draft = Event.objects.create(
            title="Dateless Draft",
            start_datetime=None,
            datetime_tbd=False,
            created_by=creator,
            status=EventStatus.DRAFT,
        )
        response = api_client.patch(
            f"/api/community/events/{draft.id}/",
            data=json.dumps({"status": "active"}),
            content_type="application/json",
            **creator_headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Event.START_DATETIME_REQUIRED_UNLESS_TBD, "start_datetime")
        draft.refresh_from_db()
        assert draft.status == EventStatus.DRAFT

    def test_publish_dateless_draft_with_tbd_succeeds(self, api_client, creator_headers, creator):
        """A draft with no start_datetime but datetime_tbd=True can be published."""
        draft = Event.objects.create(
            title="TBD Dateless Draft",
            start_datetime=None,
            datetime_tbd=True,
            created_by=creator,
            status=EventStatus.DRAFT,
        )
        response = api_client.patch(
            f"/api/community/events/{draft.id}/",
            data=json.dumps({"status": "active"}),
            content_type="application/json",
            **creator_headers,
        )
        assert response.status_code == 200

    def test_publish_tbd_draft_with_past_start_ok(self, api_client, creator_headers, creator):
        """datetime_tbd=True drafts skip the future-date check on publish."""
        draft = Event.objects.create(
            title="TBD Draft",
            start_datetime=past_iso(days=90),
            datetime_tbd=True,
            created_by=creator,
            status=EventStatus.DRAFT,
        )
        response = api_client.patch(
            f"/api/community/events/{draft.id}/",
            data=json.dumps({"status": "active"}),
            content_type="application/json",
            **creator_headers,
        )
        assert response.status_code == 200

    def test_publish_requires_edit_permission(self, api_client, sample_draft, other_headers):
        response = api_client.patch(
            f"/api/community/events/{sample_draft.id}/",
            data=json.dumps({"status": "active"}),
            content_type="application/json",
            **other_headers,
        )
        assert response.status_code == 403

    def test_cohost_can_publish_draft(self, api_client, sample_draft, cohost, cohost_headers):
        sample_draft.co_hosts.add(cohost)
        response = api_client.patch(
            f"/api/community/events/{sample_draft.id}/",
            data=json.dumps({"status": "active"}),
            content_type="application/json",
            **cohost_headers,
        )
        assert response.status_code == 200

    def test_active_to_draft_rejected(self, api_client, future_active_event, creator_headers):
        response = api_client.patch(
            f"/api/community/events/{future_active_event.id}/",
            data=json.dumps({"status": "draft"}),
            content_type="application/json",
            **creator_headers,
        )
        assert response.status_code == 400
