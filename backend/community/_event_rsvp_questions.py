"""CRUD endpoints for per-event RSVP questions."""

import logging
from uuid import UUID

from config.audit import audit_log
from config.auth import gated_jwt
from django.db import transaction
from django.db.models import Max
from ninja import Router
from ninja.responses import Status

from community._event_schemas import (
    EventRsvpQuestionIn,
    EventRsvpQuestionOut,
    EventRsvpQuestionSyncPayload,
    validate_event_rsvp_question,
)
from community._events import _can_edit_event
from community._shared import ErrorOut
from community._validation import Code, raise_validation
from community.models import Event, EventRsvpQuestion

router = Router()


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


@router.post(
    "/events/{event_id}/rsvp-questions/",
    response={
        201: EventRsvpQuestionOut,
        400: ErrorOut,
        403: ErrorOut,
        404: ErrorOut,
        409: ErrorOut,
        422: ErrorOut,
    },
    auth=gated_jwt,
)
@transaction.atomic
def create_event_rsvp_question(request, event_id: UUID, payload: EventRsvpQuestionIn):
    event = _load_editable_event(request, event_id)
    Event.objects.select_for_update().get(id=event.id)
    validate_event_rsvp_question(payload)
    max_order = event.rsvp_questions.aggregate(m=Max("display_order"))["m"]
    next_order = 0 if max_order is None else max_order + 1
    q = EventRsvpQuestion.objects.create(
        event=event,
        label=payload.label,
        field_type=payload.field_type,
        options=payload.options,
        required=payload.required,
        display_order=next_order,
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


@router.put(
    "/events/{event_id}/rsvp-questions/",
    response={
        200: list[EventRsvpQuestionOut],
        400: ErrorOut,
        403: ErrorOut,
        404: ErrorOut,
        422: ErrorOut,
    },
    auth=gated_jwt,
)
@transaction.atomic
def replace_event_rsvp_questions(request, event_id: UUID, payload: EventRsvpQuestionSyncPayload):
    event = _load_editable_event(request, event_id)
    Event.objects.select_for_update().get(id=event.id)
    for item in payload.questions:
        validate_event_rsvp_question(item)

    existing = {
        question.id: question
        for question in EventRsvpQuestion.objects.select_for_update().filter(event=event)
    }
    current = sorted(existing.values(), key=lambda question: question.display_order)
    current_state = [
        (question.id, question.label, question.field_type, question.options, question.required)
        for question in current
    ]
    expected_state = [
        (item.id, item.label, item.field_type, item.options, item.required)
        for item in payload.expected
    ]
    if current_state != expected_state:
        raise_validation(Code.Event.RSVP_QUESTION_CONFLICT, status_code=409)

    requested_ids = [item.id for item in payload.questions if item.id is not None]
    if len(requested_ids) != len(set(requested_ids)):
        raise_validation(
            Code.Event.RSVP_QUESTION_DUPLICATE,
            field="questions.id",
            status_code=400,
        )
    if any(question_id not in existing for question_id in requested_ids):
        raise_validation(Code.Event.RSVP_QUESTION_NOT_FOUND, status_code=404)

    synced = []
    for display_order, item in enumerate(payload.questions):
        question = existing.get(item.id) if item.id is not None else None
        if question is None:
            question = EventRsvpQuestion(event=event)
        question.label = item.label
        question.field_type = item.field_type
        question.options = item.options
        question.required = item.required
        question.display_order = display_order
        question.save()
        synced.append(question)

    keep_ids = {question.id for question in synced}
    EventRsvpQuestion.objects.filter(event=event).exclude(id__in=keep_ids).delete()
    audit_log(
        logging.INFO,
        "event_rsvp_questions_replaced",
        request,
        target_type="event",
        target_id=str(event_id),
        details={"question_count": len(synced)},
    )
    return Status(200, [_question_out(question) for question in synced])


@router.patch(
    "/events/{event_id}/rsvp-questions/{question_id}/",
    response={
        200: EventRsvpQuestionOut,
        400: ErrorOut,
        403: ErrorOut,
        404: ErrorOut,
        422: ErrorOut,
    },
    auth=gated_jwt,
)
def update_event_rsvp_question(
    request, event_id: UUID, question_id: UUID, payload: EventRsvpQuestionIn
):
    _load_editable_event(request, event_id)
    validate_event_rsvp_question(payload)
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
