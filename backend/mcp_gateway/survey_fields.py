from typing import Annotated, Literal, Self
from uuid import UUID

from community._field_limits import FieldLimit
from community._survey_schemas import SurveyIn, SurveyQuestionIn
from community.models import ShowIfOperator, SurveyVisibility
from django.utils.text import slugify
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from mcp_gateway.fields import WHEN, NewYorkTime, build

_NEEDS_OPTIONS = ("radio", "select", "checkbox")
_TYPES = "text: short answer; textarea: long answer; number; boolean: yes/no; radio: pick one "
_TYPES += "(buttons); select: pick one (dropdown); checkbox: pick any"
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
# A real id only exists once the source question is created; validation just needs a UUID.
_PENDING_ID = UUID(int=0)


class ShowIf(BaseModel):
    model_config = ConfigDict(extra="forbid")

    position: int = Field(ge=1, description="1-based position of an earlier question in the list")
    operator: ShowIfOperator = Field(ShowIfOperator.EQUALS, description="contains: checkbox only")
    value: str = Field(description="one of the source's options, or yes/no for a boolean source")


class SurveyQuestionFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: Text = Field(description="the question as respondents see it")
    field_type: Literal["text", "textarea", "number", "boolean", "radio", "select", "checkbox"] = (
        Field("text", description=_TYPES)
    )
    options: list[str] = Field([], description="radio/select/checkbox: the choices; else none")
    required: bool = Field(False, description="respondents must answer it")
    show_if: ShowIf | None = Field(
        None,
        description="show it only when an earlier radio/select/checkbox/boolean answer matches",
    )

    @model_validator(mode="after")
    def _shape_options(self) -> Self:
        kind, self.options = self.field_type, [o.strip() for o in self.options if o.strip()]
        if kind in _NEEDS_OPTIONS and not self.options:
            raise ValueError(f"{kind} questions need at least one option")
        if kind not in _NEEDS_OPTIONS and self.options:
            raise ValueError(f"{kind} questions take no options")
        return self


def _sources_are_earlier(questions: list[SurveyQuestionFields]) -> list[SurveyQuestionFields]:
    for position, question in enumerate(questions, start=1):
        if question.show_if and question.show_if.position >= position:
            raise ValueError(f"question {position}'s show_if must point at an earlier question")
    return questions


SurveyQuestions = Annotated[
    list[SurveyQuestionFields],
    Field(min_length=1, description="in the order respondents see them"),
    AfterValidator(_sources_are_earlier),
]


class SurveySettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Text = Field(description="survey title")
    description: str = Field("", description="intro shown above the questions")
    slug: str = Field("", description="url segment, /surveys/<slug>; empty: made from the title")
    visibility: SurveyVisibility = Field(SurveyVisibility.PUBLIC, description="who can answer")
    anonymous: bool = Field(False, description="responses aren't tied to a member")
    one_response_per_user: bool = Field(False, description="each person can answer only once")
    opens_at: NewYorkTime = Field(None, description=f"first time it takes responses, {WHEN}")
    closes_at: NewYorkTime = Field(None, description=f"stops taking responses, {WHEN}")
    max_responses: int | None = Field(None, description="stop after this many; empty: unlimited")
    linked_event_id: UUID | None = Field(None, description="event id this survey is for")
    confirmation_message: str = Field("", description="shown to the respondent after submitting")


def to_survey_in(settings: SurveySettings) -> SurveyIn:
    slug = slugify(settings.slug or settings.title)[: FieldLimit.SLUG].strip("-")
    if not slug:
        raise ToolError("give a slug: the title has no letters or numbers to make one from")
    return build(SurveyIn, {**settings.model_dump(mode="json"), "slug": slug, "is_active": False})


def to_question_in(question: SurveyQuestionFields) -> tuple[int, SurveyQuestionIn]:
    """return(tuple): the show_if source's position (0: none), and the payload."""
    data = question.model_dump(mode="json", exclude={"show_if"})
    if question.show_if is None:
        return 0, build(SurveyQuestionIn, data)
    condition = question.show_if.model_dump(mode="json", exclude={"position"})
    data["show_if"] = {**condition, "question_id": _PENDING_ID}
    return question.show_if.position, build(SurveyQuestionIn, data)
