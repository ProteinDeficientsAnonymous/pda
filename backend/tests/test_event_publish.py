import json

import pytest
from community._validation import Code
from community.models import Event, EventRSVP, EventStatus, RSVPStatus
from ninja_jwt.tokens import RefreshToken
from notifications.models import Notification, NotificationType
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

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


@pytest.fixture
def past_active_event(db, creator):
    """A past ACTIVE event with zero RSVPs — unpublish must still be rejected."""
    return Event.objects.create(
        title="Past Active BBQ",
        start_datetime=past_iso(days=90),
        end_datetime=past_iso(days=90),
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


@pytest.mark.django_db
class TestUnpublishActive:
    def test_active_to_draft_with_no_rsvps(self, api_client, future_active_event, creator_headers):
        before = Notification.objects.count()
        response = api_client.patch(
            f"/api/community/events/{future_active_event.id}/",
            data=json.dumps({"status": "draft"}),
            content_type="application/json",
            **creator_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "draft"
        assert Notification.objects.count() == before
        future_active_event.refresh_from_db()
        assert future_active_event.status == EventStatus.DRAFT

    def test_cohost_can_unpublish(self, api_client, future_active_event, cohost, cohost_headers):
        future_active_event.co_hosts.add(cohost)
        response = api_client.patch(
            f"/api/community/events/{future_active_event.id}/",
            data=json.dumps({"status": "draft"}),
            content_type="application/json",
            **cohost_headers,
        )
        assert response.status_code == 200
        future_active_event.refresh_from_db()
        assert future_active_event.status == EventStatus.DRAFT

    def test_manager_without_host_role_can_unpublish(
        self, api_client, future_active_event, other_member, other_headers
    ):
        role = Role.objects.create(name="unpublish_mgr", permissions=[PermissionKey.MANAGE_EVENTS])
        other_member.roles.add(role)
        response = api_client.patch(
            f"/api/community/events/{future_active_event.id}/",
            data=json.dumps({"status": "draft"}),
            content_type="application/json",
            **other_headers,
        )
        assert response.status_code == 200
        future_active_event.refresh_from_db()
        assert future_active_event.status == EventStatus.DRAFT

    def test_cancelled_to_draft_rejected(
        self, api_client, future_active_event, creator_headers, other_member
    ):
        EventRSVP.objects.create(
            event=future_active_event, user=other_member, status=RSVPStatus.ATTENDING
        )
        cancelled = api_client.patch(
            f"/api/community/events/{future_active_event.id}/",
            data=json.dumps({"status": "cancelled", "notify_attendees": False}),
            content_type="application/json",
            **creator_headers,
        )
        assert cancelled.status_code == 200
        response = api_client.patch(
            f"/api/community/events/{future_active_event.id}/",
            data=json.dumps({"status": "draft"}),
            content_type="application/json",
            **creator_headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Event.INVALID_STATUS_TRANSITION)

    def test_host_only_rsvps_do_not_block_unpublish(
        self, api_client, future_active_event, creator, creator_headers, cohost
    ):
        # The host crew's own rsvps (creator + co-host) are excluded from the
        # guard — only rsvps from outside the crew block unpublish.
        future_active_event.co_hosts.add(cohost)
        EventRSVP.objects.create(
            event=future_active_event, user=creator, status=RSVPStatus.ATTENDING
        )
        EventRSVP.objects.create(
            event=future_active_event, user=cohost, status=RSVPStatus.ATTENDING
        )
        detail = api_client.get(
            f"/api/community/events/{future_active_event.id}/", **creator_headers
        )
        assert detail.status_code == 200
        assert detail.json()["guest_rsvp_count"] == 0
        response = api_client.patch(
            f"/api/community/events/{future_active_event.id}/",
            data=json.dumps({"status": "draft"}),
            content_type="application/json",
            **creator_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "draft"
        future_active_event.refresh_from_db()
        assert future_active_event.status == EventStatus.DRAFT

    def test_active_to_draft_with_rsvp_rejected(
        self, api_client, future_active_event, creator_headers, cohost, other_member
    ):
        # Any RSVP row from OUTSIDE the host crew blocks the transition — even
        # can't-go. A co-host rsvp alone wouldn't, but adding an other-member
        # rsvp must still reject: the guard is "has anyone outside the host
        # crew rsvp'd at all", not "is anyone attending".
        future_active_event.co_hosts.add(cohost)
        EventRSVP.objects.create(
            event=future_active_event, user=cohost, status=RSVPStatus.ATTENDING
        )
        EventRSVP.objects.create(
            event=future_active_event, user=other_member, status=RSVPStatus.CANT_GO
        )
        detail = api_client.get(
            f"/api/community/events/{future_active_event.id}/", **creator_headers
        )
        assert detail.status_code == 200
        assert detail.json()["guest_rsvp_count"] == 1
        response = api_client.patch(
            f"/api/community/events/{future_active_event.id}/",
            data=json.dumps({"status": "draft"}),
            content_type="application/json",
            **creator_headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Event.HAS_RSVPS)
        future_active_event.refresh_from_db()
        assert future_active_event.status == EventStatus.ACTIVE

    def test_unpublish_requires_edit_permission(
        self, api_client, future_active_event, other_headers
    ):
        response = api_client.patch(
            f"/api/community/events/{future_active_event.id}/",
            data=json.dumps({"status": "draft"}),
            content_type="application/json",
            **other_headers,
        )
        assert response.status_code == 403
        future_active_event.refresh_from_db()
        assert future_active_event.status == EventStatus.ACTIVE

    def test_field_edit_rolls_back_when_unpublish_rejected(
        self, api_client, future_active_event, creator_headers, other_member
    ):
        EventRSVP.objects.create(
            event=future_active_event, user=other_member, status=RSVPStatus.ATTENDING
        )
        response = api_client.patch(
            f"/api/community/events/{future_active_event.id}/",
            data=json.dumps({"title": "new title", "status": "draft"}),
            content_type="application/json",
            **creator_headers,
        )
        assert response.status_code == 400
        future_active_event.refresh_from_db()
        assert future_active_event.title == "Active BBQ"
        assert future_active_event.status == EventStatus.ACTIVE

    def test_past_event_unpublish_rejected(self, api_client, past_active_event, creator_headers):
        # A past active event can't go back to draft: republish would 400 on
        # the future-date check and every edit would 422 — it would be stuck.
        response = api_client.patch(
            f"/api/community/events/{past_active_event.id}/",
            data=json.dumps({"status": "draft"}),
            content_type="application/json",
            **creator_headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Event.PAST_CANNOT_BE_UNPUBLISHED)
        past_active_event.refresh_from_db()
        assert past_active_event.status == EventStatus.ACTIVE


@pytest.mark.django_db
class TestRepublishNotifications:
    @staticmethod
    def _invite_count(event, user) -> int:
        return Notification.objects.filter(
            event=event, notification_type=NotificationType.EVENT_INVITE, recipient=user
        ).count()

    @staticmethod
    def _patch_status(api_client, headers, event_id, status) -> None:
        response = api_client.patch(
            f"/api/community/events/{event_id}/",
            data=json.dumps({"status": status}),
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 200

    def test_republish_cycle_leaves_each_invitee_with_exactly_one(
        self, api_client, sample_draft, creator_headers, invitee, other_member
    ):
        # New semantics: unpublish deletes the in-app invites, so the invariant
        # is "exactly one existing row after the cycle", not "notified once ever".
        sample_draft.invited_users.add(invitee)
        self._patch_status(api_client, creator_headers, sample_draft.id, "active")
        assert self._invite_count(sample_draft, invitee) == 1

        self._patch_status(api_client, creator_headers, sample_draft.id, "draft")
        assert self._invite_count(sample_draft, invitee) == 0

        # New invitee joins while draft — their first invite arrives on republish.
        sample_draft.invited_users.add(other_member)
        self._patch_status(api_client, creator_headers, sample_draft.id, "active")

        assert self._invite_count(sample_draft, invitee) == 1
        assert self._invite_count(sample_draft, other_member) == 1

    def test_unpublish_leaves_non_invite_notifications_alone(
        self, api_client, future_active_event, creator_headers, other_member
    ):
        invite = Notification.objects.create(
            recipient=other_member,
            notification_type=NotificationType.EVENT_INVITE,
            event=future_active_event,
            message="you're invited",
        )
        comment = Notification.objects.create(
            recipient=other_member,
            notification_type=NotificationType.EVENT_COMMENT,
            event=future_active_event,
            message="left a comment",
        )
        self._patch_status(api_client, creator_headers, future_active_event.id, "draft")

        assert not Notification.objects.filter(pk=invite.pk).exists()
        assert Notification.objects.filter(pk=comment.pk).exists()
