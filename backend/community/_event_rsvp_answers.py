"""Validate and snapshot RSVP question answers."""

from community._field_limits import FieldLimit
from community._question_answers import (
    assert_single_choice_member,
    is_answer_empty,
    normalize_checkbox_csv,
)
from community._validation import Code, raise_validation
from community.models import EventRsvpQuestion, RsvpQuestionType, RSVPStatus

AnswersIn = dict[str, str]


def answers_required_for_status(status: str) -> bool:
    return status in {
        RSVPStatus.ATTENDING,
        RSVPStatus.MAYBE,
        RSVPStatus.WAITLISTED,
    }


def _require_if_needed(q: EventRsvpQuestion, *, require_answers: bool) -> None:
    if require_answers and q.required:
        raise_validation(
            Code.Event.RSVP_ANSWER_REQUIRED,
            field=f"answers.{q.id}",
            label=q.label,
        )


def _normalize_answer(q: EventRsvpQuestion, answer: str) -> str:
    field = f"answers.{q.id}"
    if q.field_type == RsvpQuestionType.CHECKBOX:
        return normalize_checkbox_csv(
            answer,
            q.options,
            code=Code.Event.RSVP_ANSWER_INVALID_OPTION,
            field=field,
            label=q.label,
        )

    text = str(answer).strip()
    if q.field_type == RsvpQuestionType.SELECT:
        assert_single_choice_member(
            text,
            q.options,
            code=Code.Event.RSVP_ANSWER_INVALID_OPTION,
            field=field,
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
        if is_answer_empty(answer):
            _require_if_needed(q, require_answers=require_answers)
            continue
        assert answer is not None
        if len(answer) > FieldLimit.DESCRIPTION:
            raise_validation(
                Code.Event.RSVP_ANSWER_TOO_LONG,
                field=f"answers.{key}",
                label=q.label,
                max=FieldLimit.DESCRIPTION,
            )
        normalized = _normalize_answer(q, answer)
        # Checkbox ",,," normalizes to "" — treat as unanswered.
        if is_answer_empty(normalized):
            _require_if_needed(q, require_answers=require_answers)
            continue
        snapshot[key] = {"label": q.label, "answer": normalized}
    return snapshot
