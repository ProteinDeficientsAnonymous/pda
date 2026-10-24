from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta

from users.models import User

from community.models import (
    AttendanceStatus,
    Event,
    EventFeedbackRequest,
    EventType,
    RSVPStatus,
    Survey,
    SurveyQuestion,
    SurveyQuestionType,
    SurveyResponse,
)

from ._seed_event_feedback import seed_feedback_survey
from ._seed_shared import SeedEvent, apply_rsvp

FEEDBACK_SURVEY_SLUG = "staging-event-feedback"
FEEDBACK_TITLE_PREFIX = "[staging] feedback · "


@dataclass(frozen=True)
class FeedbackEventSpec:
    event: SeedEvent
    attendees: int
    responders: int


# Ended >7 days ago so the daily cron never emails these seeded attendees.
FEEDBACK_EVENT_SPECS = [
    FeedbackEventSpec(
        SeedEvent(
            title=f"{FEEDBACK_TITLE_PREFIX}potluck picnic",
            description="past official event with feedback responses.",
            delta_days=-10,
            duration_hours=3,
            location="riverside park",
            event_type=EventType.OFFICIAL,
            rsvp_enabled=True,
        ),
        attendees=10,
        responders=7,
    ),
    FeedbackEventSpec(
        SeedEvent(
            title=f"{FEEDBACK_TITLE_PREFIX}film night",
            description="past official event with feedback responses.",
            delta_days=-17,
            duration_hours=2,
            location="community center",
            event_type=EventType.OFFICIAL,
            rsvp_enabled=True,
        ),
        attendees=7,
        responders=4,
    ),
    FeedbackEventSpec(
        SeedEvent(
            title=f"{FEEDBACK_TITLE_PREFIX}cooking class",
            description="past official event with feedback responses.",
            delta_days=-24,
            duration_hours=2,
            location="shared kitchen",
            event_type=EventType.OFFICIAL,
            rsvp_enabled=True,
        ),
        attendees=5,
        responders=2,
    ),
]
FEEDBACK_EVENTS = [spec.event for spec in FEEDBACK_EVENT_SPECS]

CHOICE_SKEW = (0, 1, 0, 2, 1, 0, 3, 1)
TEXT_ANSWERS = {
    "what did you love?": [
        "meeting so many new people",
        "the food was incredible",
        "felt really welcoming for a first-timer",
        "",
        "the hosts kept things flowing",
        "great conversations",
    ],
    "what's your constructive feedback?": [
        "",
        "start time was a little early",
        "more seating would help",
        "",
        "hard to find the spot — maybe a sign?",
    ],
}
GENERIC_TEXT = ["loved it", "", "would come again", "a bit crowded", ""]


def _skew(index: int) -> int:
    return CHOICE_SKEW[index % len(CHOICE_SKEW)]


def _choice_answer(question: SurveyQuestion, index: int) -> str | None:
    options = question.options or []
    return options[_skew(index) % len(options)] if options else None


def _text_answer(question: SurveyQuestion, index: int) -> str | None:
    pool = TEXT_ANSWERS.get(question.label, GENERIC_TEXT)
    return pool[index % len(pool)] or None


_ANSWER_BUILDERS: dict[str, Callable[[SurveyQuestion, int], str | None]] = {
    SurveyQuestionType.RADIO: _choice_answer,
    SurveyQuestionType.SELECT: _choice_answer,
    SurveyQuestionType.CHECKBOX: _choice_answer,
    SurveyQuestionType.TEXT: _text_answer,
    SurveyQuestionType.TEXTAREA: _text_answer,
    SurveyQuestionType.RATING: lambda _q, i: str(5 - _skew(i)),
    SurveyQuestionType.BOOLEAN: lambda _q, i: "no" if i % 4 == 3 else "yes",
    SurveyQuestionType.NUMBER: lambda _q, i: str(i + 1),
}


def _answer_for(question: SurveyQuestion, index: int) -> str | None:
    builder = _ANSWER_BUILDERS.get(question.field_type)
    return builder(question, index) if builder else None


def _build_answers(questions: list[SurveyQuestion], index: int) -> dict:
    answers = {}
    for question in questions:
        answer = _answer_for(question, index)
        if answer is not None:
            answers[str(question.id)] = {"label": question.label, "answer": answer}
    return answers


def _official_feedback_survey(stdout, created_by: User | None) -> Survey:
    # Reuse a hand-made official feedback survey; the unique constraint allows only one.
    existing = Survey.objects.filter(feedback_event_type=EventType.OFFICIAL).first()
    if existing is not None:
        stdout.write(f"  using existing feedback survey: {existing.title}")
        return existing
    return seed_feedback_survey(
        stdout, created_by, title="[staging] event feedback", slug=FEEDBACK_SURVEY_SLUG
    )


def _seed_event_feedback(
    survey: Survey,
    questions: list[SurveyQuestion],
    event: Event,
    attendees: list[User],
    responders: int,
) -> int:
    assert event.end_datetime is not None
    first_sent = event.end_datetime + timedelta(days=1)
    created = 0
    for index, user in enumerate(attendees):
        apply_rsvp(
            event,
            user,
            {
                "status": RSVPStatus.ATTENDING,
                "attendance": AttendanceStatus.ATTENDED,
                "checked_in_at": event.start_datetime,
            },
            overwrite=True,
        )
        request, _ = EventFeedbackRequest.objects.get_or_create(
            event=event,
            user=user,
            defaults={"token": EventFeedbackRequest.new_token(), "first_sent_at": first_sent},
        )
        if index >= responders:
            if request.reminder_sent_at is None:
                request.reminder_sent_at = first_sent + timedelta(days=3)
                request.save(update_fields=["reminder_sent_at"])
            continue
        if request.responded_on is not None:
            continue
        submitted = first_sent + timedelta(hours=2 + index * 5)
        response = SurveyResponse.objects.create(
            survey=survey, user=None, event=event, answers=_build_answers(questions, index)
        )
        SurveyResponse.objects.filter(pk=response.pk).update(submitted_at=submitted)
        request.responded_on = submitted.date()
        request.save(update_fields=["responded_on"])
        created += 1
    return created


def seed_staging_feedback(
    stdout, created_by: User | None, events_by_title: dict[str, Event], members: list[User]
) -> None:
    survey = _official_feedback_survey(stdout, created_by)
    questions = list(survey.questions.order_by("display_order"))
    for offset, spec in enumerate(FEEDBACK_EVENT_SPECS):
        event = events_by_title[spec.event.title]
        start = (offset * 3) % max(len(members), 1)
        attendees = (members[start:] + members[:start])[: spec.attendees]
        created = _seed_event_feedback(survey, questions, event, attendees, spec.responders)
        stdout.write(f"  feedback responses for {event.title}: +{created}")


def reset_staging_feedback() -> None:
    # Response.event is SET_NULL, so drop seeded responses before their events go.
    SurveyResponse.objects.filter(event__title__startswith=FEEDBACK_TITLE_PREFIX).delete()
    Survey.objects.filter(slug=FEEDBACK_SURVEY_SLUG).delete()
