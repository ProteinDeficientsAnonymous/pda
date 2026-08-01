"""CRUD endpoints for per-event RSVP questions."""

import logging
from uuid import UUID

from config.audit import audit_log
from config.auth import gated_jwt
from ninja import Router
from ninja.responses import Status

from community._event_rsvp_question_schemas import EventRsvpQuestionIn, EventRsvpQuestionOut
from community._events import _can_edit_event
from community._shared import ErrorOut
from community._validation import Code, raise_validation
from community.models import Event, EventRsvpQuestion, EventRsvpQuestionType

router = Router()

_CHOICE_TYPES = {
    EventRsvpQuestionType.DROPDOWN,
    EventRsvpQuestionType.MULTISELECT,
}


def _question_out(q: EventRsvpQuestion) -> EventRsvpQuestionOut:
    return EventRsvpQuestionOut(
        id=str(q.id),
        label=q.label,
        field_type=q.field_type,
        options=list(q.options or []),
        required=q.required,
        display_order=q.display_order,
    )


def _load_editable_event(request, event_id: UUID) -> Event:
    try:
        event = Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    if not _can_edit_event(request.auth, event):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type="event",
            target_id=str(event_id),
            details={"endpoint": "event_rsvp_questions", "required": "edit_event"},
        )
        raise_validation(Code.Event.PERM_DENIED, status_code=403, action="manage_rsvp_questions")
    return event


def _validate_question_payload(payload: EventRsvpQuestionIn) -> None:
    if payload.field_type in _CHOICE_TYPES and len(payload.options) == 0:
        raise_validation(
            Code.Event.RSVP_QUESTION_OPTIONS_REQUIRED,
            field="options",
            status_code=400,
        )


@router.post(
    "/events/{event_id}/rsvp-questions/",
    response={201: EventRsvpQuestionOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def create_event_rsvp_question(request, event_id: UUID, payload: EventRsvpQuestionIn):
    event = _load_editable_event(request, event_id)
    _validate_question_payload(payload)
    q = EventRsvpQuestion.objects.create(
        event=event,
        label=payload.label,
        field_type=payload.field_type,
        options=payload.options,
        required=payload.required,
        display_order=event.rsvp_questions.count(),
    )
    audit_log(
        logging.INFO,
        "event_rsvp_question_created",
        request,
        target_type="event_rsvp_question",
        target_id=str(q.id),
        details={"event_id": str(event_id), "label": q.label},
    )
    return Status(201, _question_out(q))


@router.patch(
    "/events/{event_id}/rsvp-questions/{question_id}/",
    response={200: EventRsvpQuestionOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def update_event_rsvp_question(
    request, event_id: UUID, question_id: UUID, payload: EventRsvpQuestionIn
):
    _load_editable_event(request, event_id)
    _validate_question_payload(payload)
    try:
        q = EventRsvpQuestion.objects.get(id=question_id, event_id=event_id)
    except EventRsvpQuestion.DoesNotExist:
        raise_validation(Code.Event.RSVP_QUESTION_NOT_FOUND, status_code=404)
    q.label = payload.label
    q.field_type = payload.field_type
    q.options = payload.options
    q.required = payload.required
    q.save()
    audit_log(
        logging.INFO,
        "event_rsvp_question_updated",
        request,
        target_type="event_rsvp_question",
        target_id=str(question_id),
        details={"event_id": str(event_id), "label": q.label},
    )
    return Status(200, _question_out(q))


@router.delete(
    "/events/{event_id}/rsvp-questions/{question_id}/",
    response={204: None, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def delete_event_rsvp_question(request, event_id: UUID, question_id: UUID):
    _load_editable_event(request, event_id)
    try:
        q = EventRsvpQuestion.objects.get(id=question_id, event_id=event_id)
    except EventRsvpQuestion.DoesNotExist:
        raise_validation(Code.Event.RSVP_QUESTION_NOT_FOUND, status_code=404)
    q.delete()
    audit_log(
        logging.INFO,
        "event_rsvp_question_deleted",
        request,
        target_type="event_rsvp_question",
        target_id=str(question_id),
        details={"event_id": str(event_id)},
    )
    return Status(204, None)
