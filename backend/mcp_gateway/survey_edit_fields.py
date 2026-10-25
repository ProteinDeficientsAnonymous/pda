from typing import Annotated, Any, Literal
from uuid import UUID

from community._field_limits import FieldLimit
from django.utils.text import slugify
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, ConfigDict, Field, create_model

from mcp_gateway.event_fields import _no_default
from mcp_gateway.fields import local_time
from mcp_gateway.survey_fields import ShowIf, SurveyQuestionFields, SurveySettings

_TIMES = ("opens_at", "closes_at")


def partial_model(model: type[BaseModel], name: str) -> Any:
    """return(type): `model` with every field optional; an explicit null only where it allows it."""
    fields = {
        key: (
            field.rebuild_annotation(),
            Field(None, description=field.description, json_schema_extra=_no_default),
        )
        for key, field in model.model_fields.items()
    }
    config = ConfigDict(extra="forbid")
    return create_model(name, __config__=config, **fields)  # ty: ignore[no-matching-overload]


SurveyChanges = partial_model(SurveySettings, "SurveyChanges")


def normalize_settings(changed: dict[str, Any], title: str) -> dict[str, Any]:
    if "slug" not in changed:
        return changed
    slug = slugify(changed["slug"] or changed.get("title") or title)[: FieldLimit.SLUG].strip("-")
    if not slug:
        raise ToolError("give a slug with letters or numbers")
    return {**changed, "slug": slug}


def settings_diff(detail: dict[str, Any], changed: dict[str, Any]) -> dict[str, Any]:
    shown = {key: local_time(v) if key in _TIMES else v for key, v in changed.items()}
    return {
        key: {"before": detail[key], "after": value}
        for key, value in shown.items()
        if detail[key] != value
    }


QuestionRef = Annotated[
    Annotated[int, Field(ge=1, strict=True)] | UUID,
    Field(description="the question's position in the survey before this edit (1: first), or id"),
]
_FORBID = ConfigDict(extra="forbid")


class EditShowIf(ShowIf):
    model_config = _FORBID

    position: int = Field(ge=1, description="position, before this edit, of an earlier question")


class EditQuestionFields(SurveyQuestionFields):
    show_if: EditShowIf | None = Field(
        None,
        description="show it only when an earlier radio/select/checkbox/boolean answer matches",
    )


QuestionChanges = partial_model(EditQuestionFields, "QuestionChanges")


class RemoveQuestion(BaseModel):
    """remove a question: its answers are hidden and show_ifs that depend on it are cleared"""

    model_config = _FORBID

    op: Literal["remove"]
    question: QuestionRef


class UpdateQuestion(BaseModel):
    """change a question"""

    model_config = _FORBID

    op: Literal["update"]
    question: QuestionRef
    changes: QuestionChanges = Field(
        description="only the fields to change; the rest stay as they are"
    )


QuestionOp = Annotated[RemoveQuestion | UpdateQuestion, Field(discriminator="op")]
QuestionOps = Annotated[
    list[QuestionOp], Field(min_length=1, description="question changes, applied in order")
]
