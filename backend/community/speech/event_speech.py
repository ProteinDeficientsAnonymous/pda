from datetime import datetime
from uuid import UUID

from config.auth import gated_jwt
from django.conf import settings
from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone
from ninja import Router
from ninja.responses import Status
from pydantic import BaseModel
from users.helpers import visible_display_name
from users.models import User

from community.events.helpers import _validated_event_format, is_cohost
from community.models import (
    Event,
    EventFormat,
    EventSpeech,
    EventStatus,
    EventType,
    PageVisibility,
    SpeechTemplate,
)
from community.shared import ErrorOut
from community.speech._render import render_speech_html
from community.speech.blanks import SpeechValues, clean_values
from community.validation import Code, raise_validation

router = Router()

_UPCOMING_LIMIT = 5


class EventSpeechIn(BaseModel):
    event_format: str | None = None
    values: dict


class EventSpeechOut(BaseModel):
    event_title: str
    event_format: str | None
    saved: bool
    values: dict[str, str | list[str]]
    html: str
    updated_at: datetime | None
    updated_by_name: str | None


def _load_event(event_id: UUID) -> Event:
    event = (
        Event.objects.select_related("speech__updated_by")
        .prefetch_related(
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
    if event.event_format != EventFormat.WALK:
        restaurant = event.location.split(",", 1)[0].strip()
    return {
        "facilitators": _join_names([visible_display_name(u, None) for u in event.co_hosts.all()]),
        "open_roles": list(template.open_roles),
        "upcoming_events": _upcoming_events(event),
        "restaurant": restaurant,
    }


def _saved_speech(event: Event) -> EventSpeech | None:
    return getattr(event, "speech", None)


def _out(event: Event, template: SpeechTemplate, viewer) -> EventSpeechOut:
    speech = _saved_speech(event)
    event_format = event.event_format or None
    if speech is None:
        return EventSpeechOut(
            event_title=event.title,
            event_format=event_format,
            saved=False,
            values=prefill_values(event, template),
            html="",
            updated_at=None,
            updated_by_name=None,
        )
    updater = speech.updated_by
    values = {**prefill_values(event, template), **speech.values}
    return EventSpeechOut(
        event_title=event.title,
        event_format=event_format,
        saved=True,
        values=values,
        html=render_speech_html(template, event_format, values) if event_format else "",
        updated_at=speech.updated_at,
        updated_by_name=visible_display_name(updater, viewer) if updater else None,
    )


@router.get(
    "/events/{event_id}/speech/",
    response={200: EventSpeechOut, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def get_event_speech(request, event_id: UUID):
    event = _load_cohost_event(request, event_id)
    return Status(200, _out(event, SpeechTemplate.get(), request.auth))


@router.put(
    "/events/{event_id}/speech/",
    response={200: EventSpeechOut, 403: ErrorOut, 404: ErrorOut, 422: ErrorOut},
    auth=gated_jwt,
)
def put_event_speech(request, event_id: UUID, payload: EventSpeechIn):
    event = _load_cohost_event(request, event_id)
    event_format = (
        _validated_event_format(payload.event_format, event.event_type) or event.event_format
    )
    if not event_format:
        raise_validation(Code.Speech.FORMAT_REQUIRED, field="event_format")
    try:
        values = clean_values(payload.values)
    except ValueError:
        raise_validation(Code.Speech.INVALID_VALUES, field="values")
    with transaction.atomic():
        if event_format != event.event_format:
            event.event_format = event_format
            event.save(update_fields=["event_format"])
        speech, _ = EventSpeech.objects.update_or_create(
            event=event, defaults={"values": values, "updated_by": request.auth}
        )
    event.speech = speech
    return Status(200, _out(event, SpeechTemplate.get(), request.auth))
