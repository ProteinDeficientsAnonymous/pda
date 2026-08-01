"""Validate and snapshot RSVP question answers."""

from community._validation import Code, raise_validation
from community.models import EventRsvpQuestion, RSVPStatus, SurveyQuestionType

AnswersIn = dict[str, str]


def answers_required_for_status(status: str) -> bool:
    return status in {
        RSVPStatus.ATTENDING,
        RSVPStatus.MAYBE,
        RSVPStatus.WAITLISTED,
    }


def _is_empty(answer: str | None) -> bool:
    return answer is None or not str(answer).strip()


def _normalize_answer(q: EventRsvpQuestion, answer: str) -> str:
    if q.field_type == SurveyQuestionType.MULTISELECT:
        cleaned = [v.strip() for v in str(answer).split(",") if v.strip()]
        options = set(q.options or [])
        for val in cleaned:
            if val not in options:
                raise_validation(
                    Code.Event.RSVP_ANSWER_INVALID_OPTION,
                    field=f"answers.{q.id}",
                    label=q.label,
                )
        return ",".join(cleaned)

    text = str(answer).strip()
    if q.field_type == SurveyQuestionType.DROPDOWN and text not in (q.options or []):
        raise_validation(
            Code.Event.RSVP_ANSWER_INVALID_OPTION,
            field=f"answers.{q.id}",
            label=q.label,
        )
    return text


def build_rsvp_answers(
    questions: list[EventRsvpQuestion],
    raw: AnswersIn | None,
    *,
    require_answers: bool,
) -> dict:
    """Return snapshot dict {qid: {label, answer}} or raise ValidationException."""
    incoming = raw or {}
    snapshot: dict = {}
    for q in questions:
        key = str(q.id)
        answer = incoming.get(key)
        if _is_empty(answer):
            if require_answers and q.required:
                raise_validation(
                    Code.Event.RSVP_ANSWER_REQUIRED,
                    field=f"answers.{key}",
                    label=q.label,
                )
            continue
        assert answer is not None
        snapshot[key] = {"label": q.label, "answer": _normalize_answer(q, answer)}
    return snapshot
