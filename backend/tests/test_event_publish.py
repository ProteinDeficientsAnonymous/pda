"""Tests for publishing and deleting draft events via status transitions."""

import json

import pytest
from community._validation import Code
from community.models import Event, EventStatus
from notifications.models import Notification

from tests._asserts import assert_error_code
from tests.conftest import future_iso, past_iso


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

    def test_field_edit_rolls_back_when_transition_rejects(
        self, api_client, future_active_event, creator_headers
    ):
        # A field edit paired with a status transition that fails must not persist
        # (update_event wraps both in one transaction).
        response = api_client.patch(
            f"/api/community/events/{future_active_event.id}/",
            data=json.dumps({"title": "Edited Title", "status": "draft"}),
            content_type="application/json",
            **creator_headers,
        )
        assert response.status_code == 400
        future_active_event.refresh_from_db()
        assert future_active_event.title == "Active BBQ"
        assert future_active_event.status == EventStatus.ACTIVE

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
