"""Tests for the draft event lifecycle: create, list, detail, publish, delete."""

import json

import pytest
from community._validation import Code
from community.models import Event, EventStatus

from tests._asserts import assert_error_code
from tests.conftest import future_iso, past_iso


@pytest.fixture
def creator(db):
    from users.models import User

    return User.objects.create_user(
        phone_number="+14155550201",
        password="creatorpass123",
        display_name="Draft Creator",
    )


@pytest.fixture
def creator_headers(creator):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(creator)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def other_member(db):
    from users.models import User

    return User.objects.create_user(
        phone_number="+14155550202",
        password="otherpass123",
        display_name="Other Member",
    )


@pytest.fixture
def other_headers(other_member):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(other_member)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def cohost(db):
    from users.models import User

    return User.objects.create_user(
        phone_number="+14155550203",
        password="cohostpass123",
        display_name="Draft Cohost",
    )


@pytest.fixture
def cohost_headers(cohost):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(cohost)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def invitee(db):
    from users.models import User

    return User.objects.create_user(
        phone_number="+14155550204",
        password="inviteepass123",
        display_name="Draft Invitee",
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
class TestCreateDraft:
    def test_create_draft_only_requires_title(self, api_client, creator_headers):
        response = api_client.post(
            "/api/community/events/",
            data=json.dumps(
                {"title": "My Draft", "start_datetime": future_iso(days=180), "status": "draft"}
            ),
            content_type="application/json",
            **creator_headers,
        )
        assert response.status_code == 201
        assert response.json()["status"] == "draft"

    def test_create_draft_past_start_rejected(self, api_client, creator_headers):
        response = api_client.post(
            "/api/community/events/",
            data=json.dumps(
                {"title": "Past Draft", "start_datetime": past_iso(days=90), "status": "draft"}
            ),
            content_type="application/json",
            **creator_headers,
        )
        assert response.status_code == 422
        assert_error_code(response, Code.Event.START_DATETIME_MUST_BE_FUTURE, "start_datetime")

    def test_create_active_event_past_start_rejected(self, api_client, creator_headers):
        response = api_client.post(
            "/api/community/events/",
            data=json.dumps(
                {
                    "title": "Past Active",
                    "start_datetime": past_iso(days=90),
                    "status": "active",
                }
            ),
            content_type="application/json",
            **creator_headers,
        )
        assert response.status_code == 422
        assert_error_code(response, Code.Event.START_DATETIME_MUST_BE_FUTURE, "start_datetime")

    def test_create_event_invalid_status_rejected(self, api_client, creator_headers):
        response = api_client.post(
            "/api/community/events/",
            data=json.dumps(
                {
                    "title": "Bad Status",
                    "start_datetime": future_iso(days=180),
                    "status": "cancelled",
                }
            ),
            content_type="application/json",
            **creator_headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Event.INVALID_CREATE_STATUS, "status")

    def test_create_draft_skips_invitee_notifications(self, api_client, creator_headers, invitee):
        from notifications.models import Notification

        response = api_client.post(
            "/api/community/events/",
            data=json.dumps(
                {
                    "title": "Draft With Invitee",
                    "start_datetime": future_iso(days=180),
                    "status": "draft",
                    "invited_user_ids": [str(invitee.pk)],
                }
            ),
            content_type="application/json",
            **creator_headers,
        )
        assert response.status_code == 201
        # Invitees should NOT be notified until publish
        assert not Notification.objects.filter(recipient=invitee).exists()

    def test_create_draft_fires_cohost_notifications(self, api_client, creator_headers, cohost):
        from notifications.models import Notification

        response = api_client.post(
            "/api/community/events/",
            data=json.dumps(
                {
                    "title": "Draft With Cohost",
                    "start_datetime": future_iso(days=180),
                    "status": "draft",
                    "co_host_ids": [str(cohost.pk)],
                }
            ),
            content_type="application/json",
            **creator_headers,
        )
        assert response.status_code == 201
        # Cohosts ARE notified immediately — they're collaborators
        assert Notification.objects.filter(recipient=cohost).exists()

    def test_create_event_unauthenticated(self, api_client):
        response = api_client.post(
            "/api/community/events/",
            data=json.dumps({"title": "Anon", "start_datetime": future_iso(days=180)}),
            content_type="application/json",
        )
        assert response.status_code == 401


@pytest.mark.django_db
class TestListDrafts:
    def test_draft_hidden_from_default_list(self, api_client, sample_draft, other_headers):
        response = api_client.get("/api/community/events/", **other_headers)
        assert response.status_code == 200
        ids = [e["id"] for e in response.json()]
        assert str(sample_draft.id) not in ids

    def test_draft_hidden_from_unauthenticated_list(self, api_client, sample_draft):
        response = api_client.get("/api/community/events/")
        assert response.status_code == 200
        ids = [e["id"] for e in response.json()]
        assert str(sample_draft.id) not in ids

    def test_draft_visible_to_creator_via_status_filter(
        self, api_client, sample_draft, creator_headers
    ):
        response = api_client.get("/api/community/events/?status=draft", **creator_headers)
        assert response.status_code == 200
        ids = [e["id"] for e in response.json()]
        assert str(sample_draft.id) in ids

    def test_draft_list_requires_auth(self, api_client, sample_draft):
        response = api_client.get("/api/community/events/?status=draft")
        assert response.status_code == 403

    def test_draft_invisible_to_other_member(self, api_client, sample_draft, other_headers):
        response = api_client.get("/api/community/events/?status=draft", **other_headers)
        assert response.status_code == 200
        ids = [e["id"] for e in response.json()]
        assert str(sample_draft.id) not in ids

    def test_draft_visible_to_cohost(self, api_client, sample_draft, cohost, cohost_headers):
        sample_draft.co_hosts.add(cohost)
        response = api_client.get("/api/community/events/?status=draft", **cohost_headers)
        assert response.status_code == 200
        ids = [e["id"] for e in response.json()]
        assert str(sample_draft.id) in ids


@pytest.mark.django_db
class TestDraftDetail:
    def test_draft_detail_visible_to_creator(self, api_client, sample_draft, creator_headers):
        response = api_client.get(f"/api/community/events/{sample_draft.id}/", **creator_headers)
        assert response.status_code == 200

    def test_draft_detail_403_for_other_member(self, api_client, sample_draft, other_headers):
        response = api_client.get(f"/api/community/events/{sample_draft.id}/", **other_headers)
        assert response.status_code == 403
        assert_error_code(response, Code.Event.PERM_DENIED)

    def test_draft_detail_403_for_unauthenticated(self, api_client, sample_draft):
        response = api_client.get(f"/api/community/events/{sample_draft.id}/")
        assert response.status_code == 403
        assert_error_code(response, Code.Event.PERM_DENIED)

    def test_draft_detail_visible_to_cohost(self, api_client, sample_draft, cohost, cohost_headers):
        sample_draft.co_hosts.add(cohost)
        response = api_client.get(f"/api/community/events/{sample_draft.id}/", **cohost_headers)
        assert response.status_code == 200


@pytest.mark.django_db
class TestPatchDraft:
    def test_patch_draft_past_datetime_rejected(self, api_client, sample_draft, creator_headers):
        response = api_client.patch(
            f"/api/community/events/{sample_draft.id}/",
            data=json.dumps({"start_datetime": past_iso(days=90)}),
            content_type="application/json",
            **creator_headers,
        )
        assert response.status_code == 422
        assert_error_code(response, Code.Event.START_DATETIME_MUST_BE_FUTURE, "start_datetime")

    def test_patch_stale_draft_rejects_unrelated_field_edits(
        self, api_client, creator, creator_headers
    ):
        """A draft whose start slipped into the past can't be saved until the
        date is updated — even if the user only touches the title."""
        stale = Event.objects.create(
            title="Old Draft",
            start_datetime=past_iso(days=90),
            created_by=creator,
            status=EventStatus.DRAFT,
        )
        response = api_client.patch(
            f"/api/community/events/{stale.id}/",
            data=json.dumps({"title": "new title"}),
            content_type="application/json",
            **creator_headers,
        )
        assert response.status_code == 422
        assert_error_code(response, Code.Event.START_DATETIME_MUST_BE_FUTURE, "start_datetime")

    def test_patch_startless_draft_title_succeeds(self, api_client, creator, creator_headers):
        """A draft with no start_datetime at all should still be editable —
        progress-capture drafts are allowed to be dateless (see #357)."""
        startless = Event.objects.create(
            title="Dateless Draft",
            start_datetime=None,
            datetime_tbd=False,
            created_by=creator,
            status=EventStatus.DRAFT,
        )
        response = api_client.patch(
            f"/api/community/events/{startless.id}/",
            data=json.dumps({"title": "new title"}),
            content_type="application/json",
            **creator_headers,
        )
        assert response.status_code == 200

    def test_patch_draft_title(self, api_client, sample_draft, creator_headers):
        response = api_client.patch(
            f"/api/community/events/{sample_draft.id}/",
            data=json.dumps({"title": "Updated Draft Title"}),
            content_type="application/json",
            **creator_headers,
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Draft Title"

    def test_patch_draft_cohost_adds_fires_notification(
        self, api_client, sample_draft, creator_headers, cohost
    ):
        from notifications.models import Notification

        response = api_client.patch(
            f"/api/community/events/{sample_draft.id}/",
            data=json.dumps({"co_host_ids": [str(cohost.pk)]}),
            content_type="application/json",
            **creator_headers,
        )
        assert response.status_code == 200
        assert Notification.objects.filter(recipient=cohost).exists()


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
        from notifications.models import Notification

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


@pytest.mark.django_db
class TestDeleteDraft:
    def test_draft_to_deleted_allowed(self, api_client, sample_draft, creator_headers):
        response = api_client.patch(
            f"/api/community/events/{sample_draft.id}/",
            data=json.dumps({"status": "deleted"}),
            content_type="application/json",
            **creator_headers,
        )
        assert response.status_code == 200
        sample_draft.refresh_from_db()
        assert sample_draft.status == EventStatus.DELETED

    def test_draft_delete_requires_permission(self, api_client, sample_draft, other_headers):
        response = api_client.patch(
            f"/api/community/events/{sample_draft.id}/",
            data=json.dumps({"status": "deleted"}),
            content_type="application/json",
            **other_headers,
        )
        assert response.status_code == 403
