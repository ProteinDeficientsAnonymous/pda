import uuid

import pytest
from community.models import Event, EventStatus, EventType, PageVisibility
from django.utils import timezone
from users.models import User


@pytest.mark.django_db
class TestSingleEventIcs:
    def test_returns_ics_for_existing_event(self, api_client, test_user):
        event = Event.objects.create(
            title="Picnic in the Park",
            description="Bring hummus!",
            location="Prospect Park",
            start_datetime=timezone.now(),
            created_by=test_user,
        )

        resp = api_client.get(f"/api/community/events/{event.id}/ics/")
        assert resp.status_code == 200
        assert resp["Content-Type"] == "text/calendar"
        content = resp.content.decode()
        assert "BEGIN:VCALENDAR" in content
        assert "Picnic in the Park" in content
        assert "Prospect Park" in content

    def test_returns_404_for_nonexistent_event(self, api_client):
        resp = api_client.get(f"/api/community/events/{uuid.uuid4()}/ics/")
        assert resp.status_code == 404

    def test_anon_ics_omits_member_only_links(self, api_client, test_user):
        event = Event.objects.create(
            title="Linked Picnic",
            description="Bring hummus!",
            start_datetime=timezone.now(),
            whatsapp_link="https://chat.whatsapp.com/secret",
            partiful_link="https://partiful.com/e/secret",
            other_link="https://example.com/secret",
            created_by=test_user,
        )

        resp = api_client.get(f"/api/community/events/{event.id}/ics/")
        assert resp.status_code == 200
        content = resp.content.decode().replace("\r\n ", "")
        # Public fields stay; member-only links must NOT leak to anon (#445).
        assert "Bring hummus!" in content
        assert "whatsapp.com/secret" not in content
        assert "partiful.com/e/secret" not in content
        assert "example.com/secret" not in content

    def test_authed_ics_includes_member_only_links(self, api_client, auth_headers, test_user):
        event = Event.objects.create(
            title="Linked Picnic",
            description="Bring hummus!",
            start_datetime=timezone.now(),
            whatsapp_link="https://chat.whatsapp.com/secret",
            partiful_link="https://partiful.com/e/secret",
            other_link="https://example.com/secret",
            created_by=test_user,
        )

        resp = api_client.get(f"/api/community/events/{event.id}/ics/", **auth_headers)
        assert resp.status_code == 200
        content = resp.content.decode().replace("\r\n ", "")
        assert "WhatsApp: https://chat.whatsapp.com/secret" in content
        assert "Partiful: https://partiful.com/e/secret" in content
        assert "Link: https://example.com/secret" in content

    def test_invite_only_event_hidden_from_anon(self, api_client, test_user):
        creator = User.objects.create_user(
            phone_number="+12025559999",
            password="testpass123",
            display_name="Creator",
        )
        event = Event.objects.create(
            title="Secret Invite Only",
            start_datetime=timezone.now(),
            visibility=PageVisibility.INVITE_ONLY,
            created_by=creator,
        )

        resp = api_client.get(f"/api/community/events/{event.id}/ics/")
        # Matches the canonical get_event gate, which 403s invite-only for
        # non-invited/anon callers (Code.Event.PERM_DENIED).
        assert resp.status_code == 403

    def test_members_only_non_official_event_hidden_from_anon(self, api_client, test_user):
        creator = User.objects.create_user(
            phone_number="+12025558888",
            password="testpass123",
            display_name="Creator",
        )
        event = Event.objects.create(
            title="Members Only Potluck",
            description="secret address inside",
            location="123 Hidden St",
            start_datetime=timezone.now(),
            visibility=PageVisibility.MEMBERS_ONLY,
            event_type=EventType.COMMUNITY,
            created_by=creator,
        )

        resp = api_client.get(f"/api/community/events/{event.id}/ics/")
        # A members-only, non-official event must 404 for anon callers just
        # like get_event — its title/description/location must not leak.
        assert resp.status_code == 404
        body = resp.content.decode()
        assert "Members Only Potluck" not in body
        assert "secret address inside" not in body
        assert "123 Hidden St" not in body

    def test_members_only_non_official_event_visible_to_member(
        self, api_client, auth_headers, test_user
    ):
        event = Event.objects.create(
            title="Members Only Potluck",
            start_datetime=timezone.now(),
            visibility=PageVisibility.MEMBERS_ONLY,
            event_type=EventType.COMMUNITY,
            created_by=test_user,
        )

        resp = api_client.get(f"/api/community/events/{event.id}/ics/", **auth_headers)
        assert resp.status_code == 200
        assert "Members Only Potluck" in resp.content.decode()

    def test_draft_event_hidden_from_anon(self, api_client, test_user):
        creator = User.objects.create_user(
            phone_number="+12025557777",
            password="testpass123",
            display_name="Creator",
        )
        event = Event.objects.create(
            title="Unpublished Draft",
            start_datetime=timezone.now(),
            status=EventStatus.DRAFT,
            created_by=creator,
        )

        resp = api_client.get(f"/api/community/events/{event.id}/ics/")
        # Drafts are unreachable via the public API; get_event 403s them.
        assert resp.status_code == 403
        assert "Unpublished Draft" not in resp.content.decode()

    def test_deleted_event_hidden(self, api_client, auth_headers, test_user):
        event = Event.objects.create(
            title="Deleted Event",
            start_datetime=timezone.now(),
            status=EventStatus.DELETED,
            created_by=test_user,
        )

        # Even the creator can't export a deleted event via ICS (404 like get_event).
        resp = api_client.get(f"/api/community/events/{event.id}/ics/", **auth_headers)
        assert resp.status_code == 404
        assert "Deleted Event" not in resp.content.decode()

    def test_invite_only_event_visible_to_creator(self, api_client, auth_headers, test_user):
        event = Event.objects.create(
            title="Secret Invite Only",
            start_datetime=timezone.now(),
            visibility=PageVisibility.INVITE_ONLY,
            created_by=test_user,
        )

        resp = api_client.get(f"/api/community/events/{event.id}/ics/", **auth_headers)
        assert resp.status_code == 200
        assert "Secret Invite Only" in resp.content.decode()

    def test_filename_is_sanitized_against_header_injection(self, api_client, test_user):
        event = Event.objects.create(
            title='evil"\r\nSet-Cookie: x=1',
            start_datetime=timezone.now(),
            created_by=test_user,
        )

        resp = api_client.get(f"/api/community/events/{event.id}/ics/")
        assert resp.status_code == 200
        disposition = resp["Content-Disposition"]
        assert "\r" not in disposition and "\n" not in disposition
        assert disposition == f'inline; filename="event-{event.id}.ics"'
