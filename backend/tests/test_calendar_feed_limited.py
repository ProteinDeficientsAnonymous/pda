from datetime import timedelta

import pytest
from community.models import Event, EventStatus, EventType, PageVisibility
from django.utils import timezone
from users.models import MembershipStatus, User

LIMITED_STATUSES = pytest.mark.parametrize(
    "status", [MembershipStatus.TENTATIVE, MembershipStatus.ATTENDANCE_PAUSED]
)


def _event(title, event_type, visibility, *, host):
    return Event.objects.create(
        title=title,
        start_datetime=timezone.now() + timedelta(days=3),
        location=f"{title} spot",
        whatsapp_link=f"https://chat.whatsapp.com/{title.replace(' ', '')}",
        event_type=event_type,
        visibility=visibility,
        status=EventStatus.ACTIVE,
        created_by=host,
    )


@pytest.fixture
def events(db):
    host = User.objects.create_user(phone_number="+12025557100", first_name="Host")
    _event("Members Potluck", EventType.COMMUNITY, PageVisibility.MEMBERS_ONLY, host=host)
    _event("Public Picnic", EventType.COMMUNITY, PageVisibility.PUBLIC, host=host)
    _event("Official Walk", EventType.OFFICIAL, PageVisibility.MEMBERS_ONLY, host=host)


def _subscribe(membership_status):
    User.objects.create(
        phone_number="+16505551234",
        first_name="Sub",
        membership_status=membership_status,
        calendar_token="feed-token",
        guidelines_consent_at=timezone.now(),
    )


def _feed(api_client):
    resp = api_client.get("/api/community/calendar/feed/?token=feed-token")
    assert resp.status_code == 200
    return resp.content.decode().replace("\r\n ", "")


@pytest.mark.django_db
class TestLimitedCalendarFeed:
    @LIMITED_STATUSES
    def test_limited_feed_hides_members_only_community_events(self, api_client, events, status):
        _subscribe(status)
        content = _feed(api_client)
        assert "Members Potluck" not in content
        assert "Official Walk spot" in content
        assert "chat.whatsapp.com/OfficialWalk" in content

    @LIMITED_STATUSES
    def test_limited_feed_gets_public_fields_of_public_community_events(
        self, api_client, events, status
    ):
        _subscribe(status)
        content = _feed(api_client)
        assert "Public Picnic" in content
        assert "Public Picnic spot" not in content
        assert "chat.whatsapp.com/PublicPicnic" not in content

    def test_member_feed_is_unchanged(self, api_client, events):
        _subscribe(MembershipStatus.ACTIVE_MEMBER)
        content = _feed(api_client)
        for title in ("Members Potluck", "Public Picnic", "Official Walk"):
            assert f"{title} spot" in content
            assert f"chat.whatsapp.com/{title.replace(' ', '')}" in content
