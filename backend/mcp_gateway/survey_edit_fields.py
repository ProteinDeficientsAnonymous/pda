from typing import Annotated, Any, Literal
from uuid import UUID

from community._field_limits import FieldLimit
from django.utils.text import slugify
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, ConfigDict, Field, create_model

from mcp_gateway.event_fields import _no_default
from mcp_gateway.survey_fields import SurveySettings


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


QuestionRef = Annotated[
    Annotated[int, Field(ge=1, strict=True)] | UUID,
    Field(description="the question's position in the survey before this edit (1: first), or id"),
]
_FORBID = ConfigDict(extra="forbid")


class RemoveQuestion(BaseModel):
    """remove a question: its answers are hidden and show_ifs that depend on it are cleared"""

    model_config = _FORBID

    op: Literal["remove"]
    question: QuestionRef


QuestionOps = Annotated[
    list[RemoveQuestion], Field(min_length=1, description="question changes, applied in order")
]
