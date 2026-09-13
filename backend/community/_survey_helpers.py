"""Helper functions for survey output serialization and tally logic."""

from config.media_proxy import media_path
from users._helpers import visible_display_name
from users.permissions import PermissionKey

from community._survey_schemas import (
    PollResultOut,
    PollResultsOut,
    QuestionSummaryOut,
    SurveyOut,
    SurveyQuestionOut,
    SurveyResponseOut,
    VoterOut,
)
from community._validation import Code, raise_validation
from community.models import (
    DatetimePollResult,
    Event,
    PollAvailability,
    Survey,
    SurveyQuestion,
    SurveyQuestionType,
    SurveyResponse,
)

RATING_SCALE = tuple(str(n) for n in range(1, 6))
CHOICE_TYPES = frozenset(
    {SurveyQuestionType.RADIO, SurveyQuestionType.SELECT, SurveyQuestionType.CHECKBOX}
)
SUMMARIZED_TYPES = CHOICE_TYPES | {SurveyQuestionType.BOOLEAN, SurveyQuestionType.RATING}


def _survey_question_out(q: SurveyQuestion) -> SurveyQuestionOut:
    return SurveyQuestionOut(
        id=str(q.id),
        label=q.label,
        field_type=q.field_type,
        options=q.options or [],
        required=q.required,
        display_order=q.display_order,
    )


def _poll_result_out(result: DatetimePollResult) -> PollResultOut:
    return PollResultOut(
        id=str(result.id),
        winning_datetime=result.winning_datetime,
        finalized_by_id=str(result.finalized_by_id) if result.finalized_by_id else None,
        finalized_at=result.finalized_at,
    )


def _survey_out(
    survey: Survey,
    include_questions: bool = False,
    requesting_user=None,
) -> SurveyOut:
    questions = (
        [_survey_question_out(q) for q in survey.questions.all()] if include_questions else []
    )
    poll_result = None
    try:
        poll_result = _poll_result_out(survey.poll_result)
    except DatetimePollResult.DoesNotExist:
        pass
    my_response_id = None
    my_answers = None
    if requesting_user is not None:
        existing = survey.responses.filter(user=requesting_user).first()
        if existing:
            my_response_id = str(existing.id)
            my_answers = existing.answers
    return SurveyOut(
        id=str(survey.id),
        title=survey.title,
        description=survey.description,
        slug=survey.slug,
        visibility=survey.visibility,
        is_active=survey.is_active,
        one_response_per_user=survey.one_response_per_user,
        linked_event_id=str(survey.linked_event_id) if survey.linked_event_id else None,
        created_by_id=str(survey.created_by_id) if survey.created_by_id else None,
        created_at=survey.created_at,
        questions=questions,
        response_count=survey.responses.count(),
        poll_result=poll_result,
        my_response_id=my_response_id,
        my_answers=my_answers,
    )


def _apply_linked_event_update(updates: dict) -> dict:
    """Resolve linked_event_id → linked_event object in update dict.

    Raises ValidationException if the referenced event doesn't exist.
    """
    eid = updates.pop("linked_event_id")
    if not eid:
        updates["linked_event"] = None
        return updates
    try:
        updates["linked_event"] = Event.objects.get(id=eid)
    except Event.DoesNotExist:
        raise_validation(Code.Event.NOT_FOUND, field="linked_event_id", status_code=400)
    return updates


def _response_out(response: SurveyResponse, user_name: str | None) -> SurveyResponseOut:
    return SurveyResponseOut(
        id=str(response.id),
        user_id=str(response.user_id) if response.user_id else None,
        user_name=user_name,
        answers=response.answers,
        submitted_at=response.submitted_at,
    )


def _voter_out(user, viewer=None) -> VoterOut:
    return VoterOut(
        user_id=str(user.pk),
        name=visible_display_name(user, viewer),
        photo_url=media_path(user.profile_photo),
    )


def _tally_dict_answer(
    answer: dict,
    counts: dict[str, dict[str, int]],
    voters: dict[str, list[VoterOut]],
    voter: VoterOut | None,
) -> None:
    for opt, availability in answer.items():
        if opt in counts and availability in PollAvailability.VALID:
            counts[opt][availability] += 1
            if voter:
                voters[opt].append(voter)


def _tally_str_answer(
    answer: str,
    counts: dict[str, dict[str, int]],
    voters: dict[str, list[VoterOut]],
    voter: VoterOut | None,
) -> None:
    for val in answer.split(","):
        val = val.strip()
        if val in counts:
            counts[val][PollAvailability.YES] += 1
            if voter:
                voters[val].append(voter)


def _tally_question(
    q: SurveyQuestion, responses: list[SurveyResponse], viewer=None
) -> PollResultsOut:
    options = q.options or []
    counts: dict[str, dict[str, int]] = {
        opt: {PollAvailability.YES: 0, PollAvailability.MAYBE: 0} for opt in options
    }
    voters: dict[str, list[VoterOut]] = {opt: [] for opt in options}
    for r in responses:
        answer_data = r.answers.get(str(q.id))
        if not answer_data:
            continue
        answer = answer_data.get("answer")
        voter = _voter_out(r.user, viewer) if r.user else None
        if isinstance(answer, dict):
            _tally_dict_answer(answer, counts, voters, voter)
        elif isinstance(answer, str):
            _tally_str_answer(answer, counts, voters, voter)
    return PollResultsOut(
        question_id=str(q.id),
        tallies=counts,
        voters=voters,
        total_responses=len(responses),
    )


def _summary_buckets(q: SurveyQuestion) -> list[str]:
    if q.field_type == SurveyQuestionType.BOOLEAN:
        return ["yes", "no"]
    if q.field_type == SurveyQuestionType.RATING:
        return list(RATING_SCALE)
    return list(q.options or [])


def _answer_values(q: SurveyQuestion, answer: str) -> list[str]:
    if q.field_type == SurveyQuestionType.CHECKBOX:
        return [v.strip() for v in answer.split(",") if v.strip()]
    return [answer.strip()]


def _answered_values(q: SurveyQuestion, responses: list[SurveyResponse]) -> list[list[str]]:
    """Per response that answered q, the values it contributes to the tally.

    responses(list): every response on the survey, answered or not.
    return(list): one entry per answered response; checkbox entries hold many.
    """
    answers = ((r.answers.get(str(q.id)) or {}).get("answer") for r in responses)
    return [_answer_values(q, a) for a in answers if isinstance(a, str) and a.strip()]


def _rating_mean(counts: dict[str, int]) -> float | None:
    total = sum(counts.values())
    if not total:
        return None
    return round(sum(int(star) * n for star, n in counts.items()) / total, 2)


def _summarize_question(q: SurveyQuestion, responses: list[SurveyResponse]) -> QuestionSummaryOut:
    counts = dict.fromkeys(_summary_buckets(q), 0)
    answered_values = _answered_values(q, responses)
    for values in answered_values:
        for val in values:
            if val in counts:
                counts[val] += 1
    mean = _rating_mean(counts) if q.field_type == SurveyQuestionType.RATING else None
    return QuestionSummaryOut(
        question_id=str(q.id),
        field_type=q.field_type,
        counts=counts,
        answered=len(answered_values),
        mean=mean,
    )


def _csv_answer_cell(q: SurveyQuestion, answer) -> str:
    if isinstance(answer, dict):
        ordered = [opt for opt in (q.options or []) if opt in answer]
        ordered += [opt for opt in answer if opt not in ordered]
        return ";".join(f"{opt}={answer[opt]}" for opt in ordered)
    if answer is None:
        return ""
    return str(answer)


def _has_finalize_permission(request, survey: Survey, event: Event | None) -> bool:
    if request.auth.has_permission(PermissionKey.MANAGE_SURVEYS):
        return True
    if request.auth.has_permission(PermissionKey.MANAGE_EVENTS):
        return True
    if survey.created_by_id == request.auth.pk:
        return True
    if event and event.co_hosts.filter(pk=request.auth.pk).exists():
        return True
    return False
