from datetime import timedelta

import pytest
from community.models import (
    AttendanceStatus,
    Event,
    EventComment,
    EventCommentReaction,
    EventFlag,
    EventRSVP,
    JoinFormQuestion,
    ReactionEmoji,
    RSVPStatus,
    Survey,
    SurveyQuestion,
    SurveyQuestionType,
    SurveyResponse,
)
from django.utils import timezone
from users.permissions import PermissionKey

from tests._query_counts import assert_constant_queries, headers_for, make_user, make_user_with
from tests.conftest import future_iso


def _event(host, days: int = 5) -> Event:
    return Event.objects.create(
        title="Event", start_datetime=timezone.now() + timedelta(days=days), created_by=host
    )


def _rsvp(event: Event, user, **extra) -> EventRSVP:
    return EventRSVP.objects.create(event=event, user=user, status=RSVPStatus.ATTENDING, **extra)


@pytest.mark.django_db
class TestEventEndpointsQueryCount:
    def test_comments(self, api_client):
        host = make_user("Host", is_member=True)
        event = Event.objects.create(title="Chat", start_datetime=future_iso(), created_by=host)

        def grow(n: int) -> None:
            for _ in range(n):
                author = make_user("Author", is_member=True, hide_last_name=True)
                _rsvp(event, author)
                comment = EventComment.objects.create(event=event, author=author, body="hi")
                reply = EventComment.objects.create(
                    event=event, author=host, parent=comment, body="yo"
                )
                for c in (comment, reply):
                    EventCommentReaction.objects.create(
                        comment=c, user=author, emoji=ReactionEmoji.HEART
                    )

        url = f"/api/community/events/{event.id}/comments/"
        assert_constant_queries(api_client, url, grow, headers_for(host))

    @pytest.mark.parametrize("suffix", ["stats/", "text-recipients/"])
    def test_host_rsvp_views(self, api_client, suffix):
        host = make_user("Host", is_member=True)
        event = _event(host)

        def grow(n: int) -> None:
            for _ in range(n):
                _rsvp(event, make_user("Guest", is_member=True))
                event.invited_users.add(make_user("Invitee", is_member=True))

        url = f"/api/community/events/{event.id}/{suffix}"
        assert_constant_queries(api_client, url, grow, headers_for(host))

    def test_event_flags(self, api_client):
        admin = make_user_with(PermissionKey.MANAGE_EVENTS)

        def grow(n: int) -> None:
            for _ in range(n):
                flagger = make_user("Flagger", is_member=True)
                EventFlag.objects.create(event=_event(flagger), flagged_by=flagger, reason="spam")

        assert_constant_queries(api_client, "/api/community/event-flags/", grow, headers_for(admin))

    @pytest.mark.parametrize(
        "path", ["events/attendance-report/", "events/attendance-analytics/members/"]
    )
    def test_attendance_reports(self, api_client, path):
        admin = make_user_with(PermissionKey.MANAGE_EVENTS)

        def grow(n: int) -> None:
            for _ in range(n):
                member = make_user("Member", is_member=True)
                _rsvp(_event(member, days=-3), member, attendance=AttendanceStatus.ATTENDED)

        assert_constant_queries(api_client, f"/api/community/{path}", grow, headers_for(admin))


@pytest.mark.django_db
class TestContentEndpointsQueryCount:
    def test_survey_summary(self, api_client):
        admin = make_user_with(PermissionKey.MANAGE_SURVEYS)
        survey = Survey.objects.create(title="Summary", slug="summary")
        q = SurveyQuestion.objects.create(
            survey=survey, label="Rate it", field_type=SurveyQuestionType.STARS
        )

        def grow(n: int) -> None:
            for _ in range(n):
                SurveyResponse.objects.create(
                    survey=survey,
                    user=make_user("Responder"),
                    answers={str(q.id): {"label": "Rate it", "answer": "4"}},
                )

        url = f"/api/community/surveys/{survey.id}/summary/"
        assert_constant_queries(api_client, url, grow, headers_for(admin))

    def test_join_form(self, api_client):
        def grow(n: int) -> None:
            for _ in range(n):
                JoinFormQuestion.objects.create(label="Why?")

        assert_constant_queries(api_client, "/api/community/join-form/", grow)
