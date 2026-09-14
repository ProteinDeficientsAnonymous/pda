"""Helper functions for survey output serialization and tally logic."""

from config.media_proxy import media_path
from users._helpers import visible_display_name
from users.permissions import PermissionKey

from community._survey_schemas import (
    PollResultOut,
    PollResultsOut,
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
    SurveyResponse,
)


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


_MAX_ANONYMOUS_TOKEN_LENGTH = 64


def _find_my_response(
    survey: Survey, requesting_user, response_token: str
) -> SurveyResponse | None:
    if requesting_user is not None:
        return survey.responses.filter(user=requesting_user).first()
    # Only dedupe surveys mint tokens, and only their submit path reuses a row —
    # honouring a stale token elsewhere prefills a form whose submit still creates
    # a second row, orphaning the first.
    if not survey.one_response_per_user:
        return None
    # A minted token is 43 chars; anything longer can never match, so drop it
    # before an unbounded caller-supplied string reaches the index.
    if not response_token or len(response_token) > _MAX_ANONYMOUS_TOKEN_LENGTH:
        return None
    return survey.responses.filter(user__isnull=True, anonymous_token=response_token).first()


def _survey_out(
    survey: Survey,
    include_questions: bool = False,
    requesting_user=None,
    response_token: str = "",
) -> SurveyOut:
    questions = (
        [_survey_question_out(q) for q in survey.questions.all()] if include_questions else []
    )
    poll_result = None
    try:
        poll_result = _poll_result_out(survey.poll_result)
    except DatetimePollResult.DoesNotExist:
        pass
    existing = _find_my_response(survey, requesting_user, response_token)
    my_response_id = str(existing.id) if existing else None
    my_answers = existing.answers if existing else None
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


def _response_out(
    response: SurveyResponse, user_name: str | None, include_token: bool = False
) -> SurveyResponseOut:
    # The token is a bearer credential, so emitting it is opt-in: it can only
    # reach the anonymous caller that owns the row, never a listing.
    token = response.anonymous_token if include_token and response.user_id is None else None
    return SurveyResponseOut(
        id=str(response.id),
        user_id=str(response.user_id) if response.user_id else None,
        user_name=user_name,
        answers=response.answers,
        submitted_at=response.submitted_at,
        response_token=token,
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
