from typing import Annotated

from community._field_limits import FieldLimit
from community._survey_schemas import SurveyIn
from community.models import SurveyVisibility
from django.utils.text import slugify
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from mcp_gateway.fields import build

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


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
