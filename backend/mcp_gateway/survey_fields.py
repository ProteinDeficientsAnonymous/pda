from typing import Annotated, Literal, Self

from community._field_limits import FieldLimit
from community._survey_schemas import SurveyIn, SurveyQuestionIn
from community.models import SurveyVisibility
from django.utils.text import slugify
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from mcp_gateway.fields import build

_NEEDS_OPTIONS = ("radio", "select", "checkbox")
_TYPES = "text: short answer; textarea: long answer; number; boolean: yes/no; radio: pick one "
_TYPES += "(buttons); select: pick one (dropdown); checkbox: pick any"
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class SurveyQuestionFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: Text = Field(description="the question as respondents see it")
    field_type: Literal["text", "textarea", "number", "boolean", "radio", "select", "checkbox"] = (
        Field("text", description=_TYPES)
    )
    options: list[str] = Field([], description="radio/select/checkbox: the choices; else none")
    required: bool = Field(False, description="respondents must answer it")

    @model_validator(mode="after")
    def _shape_options(self) -> Self:
        kind, self.options = self.field_type, [o.strip() for o in self.options if o.strip()]
        if kind in _NEEDS_OPTIONS and not self.options:
            raise ValueError(f"{kind} questions need at least one option")
        if kind not in _NEEDS_OPTIONS and self.options:
            raise ValueError(f"{kind} questions take no options")
        return self


SurveyQuestions = Annotated[
    list[SurveyQuestionFields], Field(min_length=1, description="in the order respondents see them")
]


class SurveySettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Text = Field(description="survey title")
    description: str = Field("", description="intro shown above the questions")
    slug: str = Field("", description="url segment, /surveys/<slug>; empty: made from the title")
    visibility: SurveyVisibility = Field(SurveyVisibility.PUBLIC, description="who can answer")


def to_survey_in(settings: SurveySettings) -> SurveyIn:
    slug = slugify(settings.slug or settings.title)[: FieldLimit.SLUG].strip("-")
    if not slug:
        raise ToolError("give a slug: the title has no letters or numbers to make one from")
    return build(SurveyIn, {**settings.model_dump(mode="json"), "slug": slug, "is_active": False})


def to_question_in(question: SurveyQuestionFields) -> SurveyQuestionIn:
    return build(SurveyQuestionIn, question.model_dump(mode="json"))
