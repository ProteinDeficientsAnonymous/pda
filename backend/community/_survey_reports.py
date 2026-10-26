import csv
import io
import re
from uuid import UUID

from config.auth import gated_jwt
from django.conf import settings
from django.utils import timezone
from ninja import Router
from ninja.responses import Status
from users._helpers import visible_display_name

from community._question_answers import checkbox_values, is_answer_empty
from community._shared import ErrorOut, csv_response, csv_safe
from community._survey_schemas import QuestionSummaryOut
from community._surveys_responses import (
    _day_only,
    _load_survey_for_responses,
    _ordered_responses,
)
from community.models import Survey, SurveyQuestion, SurveyQuestionType, SurveyResponse

router = Router()

_PLAIN_NUMBER = re.compile(r"[+-]?\d+(\.\d+)?")

RATING_SCALE = tuple(str(n) for n in range(1, 6))
CHOICE_TYPES = frozenset(
    {SurveyQuestionType.RADIO, SurveyQuestionType.SELECT, SurveyQuestionType.CHECKBOX}
)
SUMMARIZED_TYPES = CHOICE_TYPES | {SurveyQuestionType.BOOLEAN, SurveyQuestionType.STARS}


def _summary_buckets(q: SurveyQuestion) -> list[str]:
    if q.field_type == SurveyQuestionType.BOOLEAN:
        return ["yes", "no"]
    if q.field_type == SurveyQuestionType.STARS:
        return list(RATING_SCALE)
    return list(q.options or [])


def _answer_values(q: SurveyQuestion, answer: str | list[str]) -> list[str]:
    if q.field_type == SurveyQuestionType.CHECKBOX:
        return checkbox_values(answer)
    return [str(answer).strip()]


def _answered_values(q: SurveyQuestion, responses: list[SurveyResponse]) -> list[list[str]]:
    """Per response that answered q, the values it contributes to the tally.

    responses(list): every response on the survey, answered or not.
    return(list): one entry per answered response; checkbox entries hold many.
    """
    answers = ((r.answers.get(str(q.id)) or {}).get("answer") for r in responses)
    return [
        _answer_values(q, a)
        for a in answers
        if isinstance(a, str | list) and not is_answer_empty(a)
    ]


def _rating_mean(counts: dict[str, int]) -> float | None:
    total = sum(counts.values())
    if not total:
        return None
    return round(sum(int(star) * n for star, n in counts.items()) / total, 2)


def _summarize_question(q: SurveyQuestion, responses: list[SurveyResponse]) -> QuestionSummaryOut:
    counts = dict.fromkeys(_summary_buckets(q), 0)
    # Choice options can be renamed/removed after responses exist; keep stale values as extra buckets.
    open_buckets = q.field_type in CHOICE_TYPES
    answered = 0
    for values in _answered_values(q, responses):
        landed = False
        for val in values:
            if val in counts or open_buckets:
                counts[val] = counts.get(val, 0) + 1
                landed = True
        answered += landed
    mean = _rating_mean(counts) if q.field_type == SurveyQuestionType.STARS else None
    return QuestionSummaryOut(
        question_id=str(q.id),
        field_type=q.field_type,
        counts=counts,
        answered=answered,
        mean=mean,
    )


def _csv_answer_cell(q: SurveyQuestion, answer) -> str:
    if isinstance(answer, dict):
        ordered = [opt for opt in (q.options or []) if opt in answer]
        ordered += [opt for opt in answer if opt not in ordered]
        return csv_safe(";".join(f"{opt}={answer[opt]}" for opt in ordered))
    if answer is None:
        return ""
    if isinstance(answer, list):
        # Options can contain "," or ";", so put one ticked option per line.
        return csv_safe("\n".join(answer))
    text = str(answer)
    # Validated numbers like -5 stay numeric in spreadsheets instead of becoming '-5 text.
    if q.field_type == SurveyQuestionType.NUMBER and _PLAIN_NUMBER.fullmatch(text):
        return text
    return csv_safe(text)


def _csv_event_cell(r: SurveyResponse) -> str:
    if not r.event:
        return ""
    start = timezone.localtime(r.event.start_datetime, settings.COMMUNITY_TZ).date()
    return csv_safe(f"{r.event.title} ({start.isoformat()})")


def _csv_row_prefix(r: SurveyResponse, survey: Survey, viewer) -> list[str]:
    event_cell = [_csv_event_cell(r)] if survey.feedback_event_type else []
    if survey.anonymous:
        return [_day_only(r.submitted_at).isoformat(), *event_cell]
    name = visible_display_name(r.user, viewer) if r.user else ""
    return [csv_safe(name), r.submitted_at.isoformat(), *event_cell]


@router.get(
    "/surveys/{survey_id}/summary/",
    response={200: list[QuestionSummaryOut], 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def get_survey_summary(request, survey_id: UUID, event_id: UUID | None = None):
    survey = _load_survey_for_responses(request, survey_id, "get_survey_summary")
    questions = [q for q in survey.questions.all() if q.field_type in SUMMARIZED_TYPES]
    responses = _ordered_responses(survey, event_id)
    return Status(200, [_summarize_question(q, responses) for q in questions])


@router.get(
    "/surveys/{survey_id}/responses.csv",
    response={403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def get_survey_responses_csv(request, survey_id: UUID):
    survey = _load_survey_for_responses(request, survey_id, "get_survey_responses_csv")
    questions = [q for q in survey.questions.all() if q.field_type != SurveyQuestionType.SECTION]
    buf = io.StringIO()
    writer = csv.writer(buf)
    labels = [csv_safe(q.label) for q in questions]
    header = ["submitted_at"] if survey.anonymous else ["submitted_by", "submitted_at"]
    if survey.feedback_event_type:
        header.append("event")
    writer.writerow([*header, *labels])
    for r in _ordered_responses(survey):
        cells = [
            _csv_answer_cell(q, (r.answers.get(str(q.id)) or {}).get("answer")) for q in questions
        ]
        writer.writerow(_csv_row_prefix(r, survey, request.auth) + cells)
    return csv_response(buf.getvalue(), f"survey-responses-{survey.slug}.csv")
