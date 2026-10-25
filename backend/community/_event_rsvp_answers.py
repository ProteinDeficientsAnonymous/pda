from users.permissions import PermissionKey

from community._field_limits import FieldLimit
from community._question_answers import (
    assert_checkbox_members,
    assert_single_choice_member,
    checkbox_values,
    is_answer_empty,
)
from community._validation import Code, raise_validation
from community.models import EventRsvpQuestion, RsvpQuestionType, RSVPStatus

RsvpAnswerIn = str | list[str]
AnswersIn = dict[str, RsvpAnswerIn]


def can_see_guest_questionnaire_responses(requesting_user, creator, co_host_ids: set[str]) -> bool:
    if requesting_user is None:
        return False
    if requesting_user.has_permission(PermissionKey.MANAGE_EVENTS):
        return True
    if creator is not None and requesting_user.pk == creator.pk:
        return True
    return str(requesting_user.pk) in co_host_ids


def find_my_questionnaire_responses(rsvps, user) -> dict:
    if user is None:
        return {}
    for r in rsvps:
        if r.user_id == user.pk:
            return dict(r.questionnaire_responses or {})
    return {}


def answers_required_for_status(status: str) -> bool:
    # Waitlisted is the capacity overflow of "going", so it still requires answers.
    return status in {RSVPStatus.ATTENDING, RSVPStatus.WAITLISTED}


def _require_if_needed(q: EventRsvpQuestion, *, require_answers: bool) -> None:
    if require_answers and q.required:
        raise_validation(
            Code.Event.RSVP_ANSWER_REQUIRED,
            field=f"questionnaire_responses.{q.id}",
            label=q.label,
        )


def _normalize_checkbox_answer(q: EventRsvpQuestion, answer: RsvpAnswerIn) -> list[str]:
    field = f"questionnaire_responses.{q.id}"
    assert_checkbox_members(
        answer,
        q.options,
        code=Code.Event.RSVP_ANSWER_INVALID_OPTION,
        field=field,
        label=q.label,
    )
    return list(dict.fromkeys(checkbox_values(answer)))


def _normalize_answer(q: EventRsvpQuestion, answer: RsvpAnswerIn) -> RsvpAnswerIn:
    if q.field_type == RsvpQuestionType.CHECKBOX:
        return _normalize_checkbox_answer(q, answer)
    field = f"questionnaire_responses.{q.id}"
    if isinstance(answer, list):
        raise_validation(Code.Event.RSVP_ANSWER_INVALID_FORMAT, field=field, label=q.label)

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
        if len("".join(answer)) > FieldLimit.DESCRIPTION:
            raise_validation(
                Code.Event.RSVP_ANSWER_TOO_LONG,
                field=f"questionnaire_responses.{key}",
                label=q.label,
                max=FieldLimit.DESCRIPTION,
            )
        normalized = _normalize_answer(q, answer)
        # Checkbox ",,," or [" "] normalizes to [] — treat as unanswered.
        if is_answer_empty(normalized):
            _require_if_needed(q, require_answers=require_answers)
            continue
        snapshot[key] = {"label": q.label, "answer": normalized}
    return snapshot
