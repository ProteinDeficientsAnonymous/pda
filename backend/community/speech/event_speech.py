from datetime import datetime
from uuid import UUID

from config.auth import gated_jwt
from django.conf import settings
from django.db.models import Prefetch
from django.utils import timezone
from ninja import Router
from ninja.responses import Status
from pydantic import BaseModel
from users.helpers import visible_display_name
from users.models import User

from community.events.helpers import is_cohost
from community.models import (
    Event,
    EventStatus,
    EventType,
    OfficialKind,
    PageVisibility,
    SpeechTemplate,
)
from community.shared import ErrorOut
from community.speech.blanks import SpeechValues
from community.validation import Code, raise_validation

router = Router()

_UPCOMING_LIMIT = 5


class EventSpeechOut(BaseModel):
    event_title: str
    official_kind: str | None
    saved: bool
    values: dict[str, str | list[str]]
    html: str
    updated_at: datetime | None
    updated_by_name: str | None


def _load_event(event_id: UUID) -> Event:
    event = (
        Event.objects.prefetch_related(
            Prefetch("co_hosts", queryset=User.objects.order_by("created_at", "pk")),
        )
        .filter(id=event_id, event_type=EventType.OFFICIAL)
        .exclude(status=EventStatus.DELETED)
        .first()
    )
    if event is None:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    return event


def _load_cohost_event(request, event_id: UUID) -> Event:
    event = _load_event(event_id)
    if not is_cohost(request.auth, {str(u.pk) for u in event.co_hosts.all()}):
        raise_validation(Code.Perm.DENIED, status_code=403, action="edit_event_speech")
    return event


def _join_names(names: list[str]) -> str:
    if len(names) <= 1:
        return "".join(names)
    return f"{', '.join(names[:-1])} and {names[-1]}"


def _format_upcoming(event: Event) -> str:
    local = event.start_datetime.astimezone(settings.COMMUNITY_TZ)  # ty: ignore[possibly-missing-attribute]
    return f"{local.month}/{local.day} {event.title}"


def _upcoming_events(event: Event) -> list[str]:
    after = max(timezone.now(), event.start_datetime) if event.start_datetime else timezone.now()
    upcoming = (
        Event.objects.filter(
            event_type=EventType.OFFICIAL,
            status=EventStatus.ACTIVE,
            visibility=PageVisibility.PUBLIC,
            start_datetime__gt=after,
        )
        .exclude(pk=event.pk)
        .order_by("start_datetime")[:_UPCOMING_LIMIT]
    )
    return [_format_upcoming(e) for e in upcoming]


def prefill_values(event: Event, template: SpeechTemplate) -> SpeechValues:
    restaurant = ""
    if event.official_kind != OfficialKind.WALK:
        restaurant = event.location.split(",", 1)[0].strip()
    return {
        "facilitators": _join_names([visible_display_name(u, None) for u in event.co_hosts.all()]),
        "open_roles": list(template.open_roles),
        "upcoming_events": _upcoming_events(event),
        "restaurant": restaurant,
    }


def _out(event: Event, template: SpeechTemplate) -> EventSpeechOut:
    kind = event.official_kind or None
    return EventSpeechOut(
        event_title=event.title,
        official_kind=kind,
        saved=False,
        values=prefill_values(event, template),
        html="",
        updated_at=None,
        updated_by_name=None,
    )


@router.get(
    "/events/{event_id}/speech/",
    response={200: EventSpeechOut, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def get_event_speech(request, event_id: UUID):
    event = _load_cohost_event(request, event_id)
    return Status(200, _out(event, SpeechTemplate.get()))
