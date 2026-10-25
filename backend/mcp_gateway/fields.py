import json
from datetime import datetime
from typing import Annotated, Any

from community._validation import ValidationException
from config.validation_handlers import _serialize_pydantic_error, _serialize_validation_exception
from django.conf import settings
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import AfterValidator, BaseModel, ValidationError

WHEN = "new york local time, e.g. 2026-11-07T11:00"


def new_york(value: datetime) -> datetime:
    local = value.replace(tzinfo=settings.COMMUNITY_TZ)
    if value.tzinfo is not None and value.utcoffset() != local.utcoffset():
        offset = local.isoformat()[-6:]
        raise ValueError(
            f"new york is at {offset} on {value.date()}; send new york local time with no offset"
        )
    return local


def _new_york_or_none(value: datetime | None) -> datetime | None:
    return None if value is None else new_york(value)


NewYorkTime = Annotated[datetime | None, AfterValidator(_new_york_or_none)]


def build[T: BaseModel](schema: type[T], data: dict[str, Any]) -> T:
    try:
        return schema(**data)
    except ValidationException as exc:
        detail = [_serialize_validation_exception(exc)]
        raise ToolError(json.dumps({"status": exc.status_code, "detail": detail})) from exc
    except ValidationError as exc:
        # The serializer drops loc[0] as ninja's handler param name; keep the real field.
        detail = [
            _serialize_pydantic_error({**err, "loc": ("payload", *err["loc"])})
            for err in exc.errors()
        ]
        raise ToolError(json.dumps({"status": 422, "detail": detail})) from exc


def local_time(value: str | None) -> str | None:
    return value and datetime.fromisoformat(value).astimezone(settings.COMMUNITY_TZ).isoformat()
