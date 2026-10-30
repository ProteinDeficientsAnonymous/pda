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


FEEDBACK_EVENT_SPECS = [
    FeedbackEventSpec(
        SeedEvent(
            title=f"{FEEDBACK_TITLE_PREFIX}{name}",
            description="past official event with feedback responses.",
            delta_days=days,
            duration_hours=2,
            location=location,
            event_type=EventType.OFFICIAL,
            rsvp_enabled=True,
        ),
        attendees,
        responders,
    )
    for name, days, location, attendees, responders in [
        ("potluck picnic", -10, "riverside park", 10, 7),
        ("film night", -17, "community center", 7, 4),
        ("cooking class", -24, "shared kitchen", 5, 2),
    ]
]
FEEDBACK_EVENTS = [spec.event for spec in FEEDBACK_EVENT_SPECS]

CHOICE_SKEW = (0, 1, 0, 2, 1, 0, 3, 1)
TEXT_ANSWERS = {
    "what did you love?": [
        "meeting so many new people",
        "the food was incredible",
        "felt really welcoming for a first-timer",
        "",
        "great conversations",
    ],
    "what's your constructive feedback?": [
        "",
        "start time was a little early",
        "more seating would help",
        "",
    ],
}
GENERIC_TEXT = ["loved it", "", "would come again", "a bit crowded"]


def _choice_answer(question: SurveyQuestion, index: int) -> str | None:
    options = question.options or []
    return options[CHOICE_SKEW[index % len(CHOICE_SKEW)] % len(options)] if options else None


def _checkbox_answer(question: SurveyQuestion, index: int) -> list[str] | None:
    choice = _choice_answer(question, index)
    return [choice] if choice is not None else None


def _text_answer(question: SurveyQuestion, index: int) -> str | None:
    pool = TEXT_ANSWERS.get(question.label, GENERIC_TEXT)
    return pool[index % len(pool)] or None


_ANSWER_BUILDERS: dict[str, Callable[[SurveyQuestion, int], str | list[str] | None]] = {
    SurveyQuestionType.RADIO: _choice_answer,
    SurveyQuestionType.SELECT: _choice_answer,
    SurveyQuestionType.CHECKBOX: _checkbox_answer,
    SurveyQuestionType.TEXT: _text_answer,
    SurveyQuestionType.TEXTAREA: _text_answer,
    SurveyQuestionType.STARS: lambda _q, i: str(5 - CHOICE_SKEW[i % len(CHOICE_SKEW)]),
    SurveyQuestionType.BOOLEAN: lambda _q, i: "no" if i % 4 == 3 else "yes",
    SurveyQuestionType.NUMBER: lambda _q, i: str(i + 1),
}


def _build_answers(questions: list[SurveyQuestion], index: int) -> dict:
    answers = {}
    for question in questions:
        builder = _ANSWER_BUILDERS.get(question.field_type)
        answer = builder(question, index) if builder else None
        if answer is not None:
            answers[str(question.id)] = {"label": question.label, "answer": answer}
    return answers


def _official_feedback_survey(stdout, created_by: User | None) -> Survey:
    # Reuse a hand-made official feedback survey; the unique constraint allows only one.
    existing = Survey.objects.filter(feedback_event_type=EventType.OFFICIAL).first()
    if existing is not None:
        return existing
    return seed_feedback_survey(
        stdout, created_by, title="[staging] event feedback", slug=FEEDBACK_SURVEY_SLUG
    )


def _seed_attendee(survey: Survey, event: Event, user: User, index: int, respond: bool) -> None:
    assert event.end_datetime is not None
    sent = event.end_datetime + timedelta(days=1)
    rsvp = {"status": RSVPStatus.ATTENDING, "attendance": AttendanceStatus.ATTENDED}
    apply_rsvp(event, user, rsvp, overwrite=True)
    request, _ = EventFeedbackRequest.objects.get_or_create(
        event=event,
        user=user,
        defaults={"token": EventFeedbackRequest.new_token(), "first_sent_at": sent},
    )
    if not respond or request.responded_on is not None:
        return
    submitted = sent + timedelta(hours=2 + index * 5)
    questions = list(survey.questions.order_by("display_order"))
    response = SurveyResponse.objects.create(
        survey=survey, event=event, answers=_build_answers(questions, index)
    )
    SurveyResponse.objects.filter(pk=response.pk).update(submitted_at=submitted)
    request.responded_on = submitted.date()
    request.save(update_fields=["responded_on"])


def seed_staging_feedback(
    stdout, created_by: User | None, events_by_title: dict[str, Event], members: list[User]
) -> None:
    survey = _official_feedback_survey(stdout, created_by)
    for offset, spec in enumerate(FEEDBACK_EVENT_SPECS):
        event = events_by_title[spec.event.title]
        start = offset * 3 % max(len(members), 1)
        attendees = (members[start:] + members[:start])[: spec.attendees]
        for index, user in enumerate(attendees):
            _seed_attendee(survey, event, user, index, index < spec.responders)
    stdout.write(f"  seeded feedback responses into survey: {survey.title}")


def reset_staging_feedback() -> None:
    # Response.event is SET_NULL, so drop seeded responses before their events go.
    SurveyResponse.objects.filter(event__title__startswith=FEEDBACK_TITLE_PREFIX).delete()
    Survey.objects.filter(slug=FEEDBACK_SURVEY_SLUG).delete()
