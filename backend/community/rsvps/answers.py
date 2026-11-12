from users.permissions import PermissionKey

from community._question_answers import (
    AnswerCodes,
    ChoiceAnswer,
    is_answer_empty,
    normalize_answer,
)
from community.field_limits import FieldLimit
from community.models import EventRsvpQuestion, RSVPStatus
from community.validation import Code, raise_validation

AnswersIn = dict[str, ChoiceAnswer]

_ANSWER_CODES = AnswerCodes(
    invalid_option=Code.Event.RSVP_ANSWER_INVALID_OPTION,
    invalid_format=Code.Event.RSVP_ANSWER_INVALID_FORMAT,
)


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
        field = f"questionnaire_responses.{key}"
        normalized = normalize_answer(answer, q, codes=_ANSWER_CODES, field=field)
        # Checkbox ",,," or [" "] normalizes to [] — treat as unanswered.
        if is_answer_empty(normalized):
            _require_if_needed(q, require_answers=require_answers)
            continue
        snapshot[key] = {"label": q.label, "answer": normalized}
    return snapshot
