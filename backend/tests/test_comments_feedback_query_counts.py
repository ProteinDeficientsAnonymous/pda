import pytest
from community._event_feedback_send import send_first_requests
from community.models import (
    Event,
    EventComment,
    EventFeedbackRequest,
    EventRSVP,
    ReactionEmoji,
    RSVPStatus,
)
from django.db import connection
from django.test.utils import CaptureQueriesContext

from tests._auth import auth_headers_for
from tests._event_comments_helpers import event  # noqa: F401
from tests.test_event_feedback_send import (  # noqa: F401
    NOW,
    feedback_survey,
    make_event,
    make_rsvp,
    make_user,
)


def _count(call) -> int:
    with CaptureQueriesContext(connection) as ctx:
        call()
    return len(ctx.captured_queries)


@pytest.mark.django_db
class TestCommentsFeedbackQueryCounts:
    def test_reaction_toggle_reuses_co_hosts_prefetch(self, api_client, event, test_user):  # noqa: F811
        viewer = make_user()
        EventRSVP.objects.create(event=event, user=viewer, status=RSVPStatus.ATTENDING)
        headers = auth_headers_for(viewer)
        top = EventComment.objects.create(event=event, author=test_user, body="top")

        for _ in range(4):
            EventComment.objects.create(event=event, author=test_user, body="r", parent=top)
        url = f"/api/community/events/{event.id}/comments/{top.id}/reactions/"
        with CaptureQueriesContext(connection) as ctx:
            response = api_client.post(
                url, {"emoji": ReactionEmoji.HEART}, content_type="application/json", **headers
            )
        assert response.status_code == 200, response.content
        # only the event's co_hosts prefetch; replies reuse it for can_delete
        table = Event.co_hosts.through._meta.db_table
        assert sum(table in q["sql"] for q in ctx.captured_queries) == 1

    def test_feedback_rerun_is_constant(self, feedback_survey, fake_email_sender):  # noqa: F811
        feedback_event = make_event()

        def add_attendees(n: int) -> None:
            for _ in range(n):
                make_rsvp(feedback_event, make_user())
            send_first_requests(NOW)

        add_attendees(2)
        small = _count(lambda: send_first_requests(NOW))
        add_attendees(6)
        assert _count(lambda: send_first_requests(NOW)) == small
        assert EventFeedbackRequest.objects.filter(first_sent_at__isnull=False).count() == 8
