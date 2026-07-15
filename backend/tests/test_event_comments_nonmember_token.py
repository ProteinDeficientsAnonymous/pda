import pytest
from community.models import Event, EventRSVP, EventType, PageVisibility, RSVPStatus
from users.models import NonMemberRsvpToken, User

from tests.conftest import future_iso


@pytest.fixture
def event(db, test_user):
    return Event.objects.create(
        title="Test Event",
        start_datetime=future_iso(days=30),
        event_type=EventType.OFFICIAL,
        visibility=PageVisibility.PUBLIC,
        rsvp_enabled=True,
        created_by=test_user,
    )


@pytest.fixture
def non_member_rsvpd(db, event):
    user = User.objects.create_user(
        phone_number="+12025550177",
        first_name="Non",
        last_name="Member",
        email="commenter@example.com",
        is_member=False,
    )
    user.set_unusable_password()
    user.save(update_fields=["password"])
    EventRSVP.objects.create(event=event, user=user, status=RSVPStatus.ATTENDING)
    return user


@pytest.fixture
def non_member_token(non_member_rsvpd):
    return NonMemberRsvpToken.issue(non_member_rsvpd).token


@pytest.mark.django_db
class TestNonMemberTokenComments:
    def test_list_comments_with_token_reports_can_post(self, api_client, event, non_member_token):
        response = api_client.get(
            f"/api/community/events/{event.id}/comments/", {"token": non_member_token}
        )
        assert response.status_code == 200, response.content
        body = response.json()
        assert body["can_post"] is True
        assert body["cannot_post_reason"] is None

    def test_post_comment_with_token_succeeds(self, api_client, event, non_member_token):
        response = api_client.post(
            f"/api/community/events/{event.id}/comments/",
            {"body": "hi from a non-member"},
            content_type="application/json",
            QUERY_STRING=f"token={non_member_token}",
        )
        assert response.status_code == 201, response.content
        assert response.json()["body"] == "hi from a non-member"

    def test_post_comment_without_rsvp_on_this_event_rejected(self, api_client, event):
        other_event = Event.objects.create(
            title="Other", start_datetime=event.start_datetime, created_by=event.created_by
        )
        user = User.objects.create_user(
            phone_number="+12025550166", first_name="No", last_name="Rsvp", is_member=False
        )
        user.set_unusable_password()
        user.save(update_fields=["password"])
        EventRSVP.objects.create(event=other_event, user=user, status=RSVPStatus.ATTENDING)
        token = NonMemberRsvpToken.issue(user).token

        response = api_client.post(
            f"/api/community/events/{event.id}/comments/",
            {"body": "should fail"},
            content_type="application/json",
            QUERY_STRING=f"token={token}",
        )
        assert response.status_code == 403, response.content

    def test_post_reply_with_token_succeeds(self, api_client, event, non_member_token):
        post_resp = api_client.post(
            f"/api/community/events/{event.id}/comments/",
            {"body": "top level"},
            content_type="application/json",
            QUERY_STRING=f"token={non_member_token}",
        )
        comment_id = post_resp.json()["id"]
        reply_resp = api_client.post(
            f"/api/community/events/{event.id}/comments/{comment_id}/replies/",
            {"body": "a reply"},
            content_type="application/json",
            QUERY_STRING=f"token={non_member_token}",
        )
        assert reply_resp.status_code == 201, reply_resp.content

    def test_delete_own_comment_with_token_succeeds(self, api_client, event, non_member_token):
        post_resp = api_client.post(
            f"/api/community/events/{event.id}/comments/",
            {"body": "delete me"},
            content_type="application/json",
            QUERY_STRING=f"token={non_member_token}",
        )
        comment_id = post_resp.json()["id"]
        delete_resp = api_client.delete(
            f"/api/community/events/{event.id}/comments/{comment_id}/",
            QUERY_STRING=f"token={non_member_token}",
        )
        assert delete_resp.status_code == 204, delete_resp.content

    def test_react_with_token_succeeds(self, api_client, event, non_member_token):
        post_resp = api_client.post(
            f"/api/community/events/{event.id}/comments/",
            {"body": "react to me"},
            content_type="application/json",
            QUERY_STRING=f"token={non_member_token}",
        )
        comment_id = post_resp.json()["id"]
        react_resp = api_client.post(
            f"/api/community/events/{event.id}/comments/{comment_id}/reactions/",
            {"emoji": "🌱"},
            content_type="application/json",
            QUERY_STRING=f"token={non_member_token}",
        )
        assert react_resp.status_code == 200, react_resp.content
