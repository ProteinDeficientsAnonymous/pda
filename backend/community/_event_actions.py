"""Event photo upload/delete endpoints."""

import logging
import time
from uuid import UUID

from config.audit import audit_log
from config.ratelimit import rate_limit
from ninja import File, Router
from ninja.files import UploadedFile
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth
from users.permissions import PermissionKey

from community._event_helpers import _event_out
from community._event_schemas import (
    _ALLOWED_IMAGE_TYPES,
    _MAX_EVENT_PHOTO_SIZE,
    EventOut,
)
from community._shared import ErrorOut
from community._validation import Code, raise_validation
from community.models import Event

router = Router()


@router.post(
    "/events/{event_id}/photo/",
    response={200: EventOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut, 429: ErrorOut},
    auth=JWTAuth(),
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="20/h")
def upload_event_photo(request, event_id: UUID, photo: UploadedFile = File(...)):  # ty: ignore[call-non-callable]
    if photo.content_type not in _ALLOWED_IMAGE_TYPES:
        raise_validation(
            Code.Photo.TYPE_NOT_ALLOWED,
            field="photo",
            status_code=400,
            allowed=sorted(_ALLOWED_IMAGE_TYPES),
        )
    if photo.size and photo.size > _MAX_EVENT_PHOTO_SIZE:
        raise_validation(
            Code.Photo.TOO_LARGE,
            field="photo",
            status_code=400,
            max_mb=_MAX_EVENT_PHOTO_SIZE // (1024 * 1024),
        )
    try:
        event = Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    is_manager = request.auth.has_permission(PermissionKey.MANAGE_EVENTS)
    is_creator = event.created_by_id == request.auth.pk
    is_cohost = event.co_hosts.filter(pk=request.auth.pk).exists()
    if not is_manager and not is_creator and not is_cohost:
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type="event",
            target_id=str(event_id),
            details={"endpoint": "upload_event_photo"},
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="upload_event_photo")
    if event.is_cancelled:
        raise_validation(Code.Event.CANCELLED_CANNOT_BE_EDITED, status_code=400)
    if event.photo:
        event.photo.delete(save=False)
    name = photo.name or ""
    ext = name.rsplit(".", 1)[-1] if "." in name else "jpg"
    ts = int(time.time())
    event.photo.save(f"{event_id}_{ts}.{ext}", photo, save=True)
    audit_log(
        logging.INFO, "event_photo_uploaded", request, target_type="event", target_id=str(event_id)
    )
    return Status(200, _event_out(event, request.auth))


@router.delete(
    "/events/{event_id}/photo/",
    response={200: EventOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def delete_event_photo(request, event_id: UUID):
    try:
        event = Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    is_manager = request.auth.has_permission(PermissionKey.MANAGE_EVENTS)
    is_creator = event.created_by_id == request.auth.pk
    is_cohost = event.co_hosts.filter(pk=request.auth.pk).exists()
    if not is_manager and not is_creator and not is_cohost:
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type="event",
            target_id=str(event_id),
            details={"endpoint": "delete_event_photo"},
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="delete_event_photo")
    if event.is_cancelled:
        raise_validation(Code.Event.CANCELLED_CANNOT_BE_EDITED, status_code=400)
    if event.photo:
        event.photo.delete(save=False)
        event.photo = ""
        event.save(update_fields=["photo"])
    audit_log(
        logging.INFO, "event_photo_deleted", request, target_type="event", target_id=str(event_id)
    )
    return Status(200, _event_out(event, request.auth))
