import logging
import os
import secrets

from config.audit import audit_log
from config.auth import gated_jwt
from config.ratelimit import rate_limit
from ninja import Router
from ninja.responses import Status
from pydantic import BaseModel, Field

from community._event_helpers import _event_out
from community._event_schemas import EventOut
from community._shared import ErrorOut
from community._validation import Code, raise_validation
from community.management.commands._seed_staging_data import is_seed_allowed
from community.models import Event, EventStatus, EventType, PageVisibility

router = Router()

TITLE_PREFIX = "[test] "
MAX_COUNT = 20


class DevTestEventIn(BaseModel):
    count: int = Field(default=1, ge=1, le=MAX_COUNT)


class DevTestEventsOut(BaseModel):
    events: list[EventOut]


def _dev_tools_allowed() -> bool:
    return is_seed_allowed(os.environ.get("RAILWAY_ENVIRONMENT_NAME"), force=False)


def _require_dev_tools(request) -> None:
    if not _dev_tools_allowed():
        raise_validation(Code.DevTools.NOT_FOUND, status_code=404)


@router.post(
    "/dev/test-events/",
    response={201: DevTestEventsOut, 404: ErrorOut},
    auth=gated_jwt,
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="30/h")
def create_dev_test_events(request, payload: DevTestEventIn):
    _require_dev_tools(request)

    events = [
        Event.objects.create(
            title=f"{TITLE_PREFIX}{secrets.token_hex(4)}",
            description="created by the dev test-events tool",
            event_type=EventType.COMMUNITY,
            visibility=PageVisibility.PUBLIC,
            status=EventStatus.DRAFT,
            created_by=request.auth,
        )
        for _ in range(payload.count)
    ]
    audit_log(
        logging.INFO,
        "dev_test_events_created",
        request,
        details={"count": len(events)},
    )
    return Status(201, DevTestEventsOut(events=[_event_out(e, request.auth) for e in events]))


@router.delete(
    "/dev/test-events/",
    response={200: DevTestEventsOut, 404: ErrorOut},
    auth=gated_jwt,
)
def delete_dev_test_events(request):
    _require_dev_tools(request)

    deleted_ids = list(
        Event.objects.filter(title__startswith=TITLE_PREFIX).values_list("id", flat=True)
    )
    Event.objects.filter(id__in=deleted_ids).delete()
    audit_log(
        logging.INFO,
        "dev_test_events_deleted",
        request,
        details={"count": len(deleted_ids)},
    )
    return Status(200, DevTestEventsOut(events=[]))
