from datetime import timedelta

import pytest
from community.models import CoHostInviteStatus, Event, EventCoHostInvite, EventType
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from users.models import NonMemberRsvpToken, User

from tests._public_rsvp_helpers import make_non_member, make_official_event


@pytest.mark.django_db
def test_past_event_detail_expires_invites_once(api_client, test_user):
    event = Event.objects.create(
        title="Over", start_datetime=timezone.now() - timedelta(days=2), created_by=test_user
    )
    event.co_hosts.add(test_user)
    invitee = User.objects.create_user(phone_number="+14155550777", first_name="Inv")
    EventCoHostInvite.objects.create(event=event, user=invitee, invited_by=test_user)
    headers = {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(test_user).access_token}"}

    with CaptureQueriesContext(connection) as ctx:
        response = api_client.get(f"/api/community/events/{event.id}/", **headers)

    assert response.status_code == 200
    assert response.json()["pending_cohost_invites"] == []
    table = EventCoHostInvite._meta.db_table
    updates = [q for q in ctx.captured_queries if q["sql"].startswith(f'UPDATE "{table}"')]
    assert len(updates) == 1
    assert EventCoHostInvite.objects.get().status == CoHostInviteStatus.EXPIRED


@pytest.mark.django_db
def test_token_viewer_reuses_loaded_event(api_client):
    nonmember = make_non_member("+14155550001", "nm@example.com", name="non member")
    token = NonMemberRsvpToken.issue_or_extend(nonmember).token
    event = make_official_event(event_type=EventType.OFFICIAL)

    with CaptureQueriesContext(connection) as ctx:
        response = api_client.get(f"/api/community/events/{event.id}/?token={token}")

    assert response.status_code == 200
    assert response.json()["location"] == event.location
    event_selects = [
        q for q in ctx.captured_queries if q["sql"].startswith('SELECT "community_event"."id"')
    ]
    assert len(event_selects) == 1
