"""Event tags endpoints.

Listing is read-only and public so the calendar and event UI can render and
filter by tag. Creating and deleting tags is gated behind the
``manage_events`` permission so admins can curate the set in-app without
Django admin.
"""

import logging
from uuid import UUID

from config.audit import audit_log
from config.auth import gated_jwt
from config.ratelimit import rate_limit
from django.db import IntegrityError, transaction
from django.utils.text import slugify
from ninja import Router
from ninja.responses import Status
from users.permissions import PermissionKey

from community._event_schemas import TagIn, TagOut
from community._shared import ErrorOut
from community._validation import Code, raise_validation
from community.models import EventTag

router = Router()


def _require_manage_tags(request, endpoint: str, target_id: str = "") -> None:
    if request.auth.has_permission(PermissionKey.MANAGE_EVENTS):
        return
    audit_log(
        logging.WARNING,
        "permission_denied",
        request,
        target_type="event_tag",
        target_id=target_id,
        details={
            "endpoint": endpoint,
            "required_permission": PermissionKey.MANAGE_EVENTS,
        },
    )
    raise_validation(Code.Perm.DENIED, status_code=403, action="manage_events")


def _tag_out(tag: EventTag) -> TagOut:
    return TagOut(id=str(tag.id), name=tag.name, slug=tag.slug)


@router.get("/event-tags/", response={200: list[TagOut]}, auth=None)
def list_event_tags(request):
    return Status(200, [_tag_out(t) for t in EventTag.objects.all()])


@router.post(
    "/event-tags/",
    response={201: TagOut, 400: ErrorOut, 403: ErrorOut, 429: ErrorOut},
    auth=gated_jwt,
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="10/m")
def create_event_tag(request, payload: TagIn):
    _require_manage_tags(request, "create_event_tag")
    name = payload.name.strip()
    if not name or not slugify(name):
        raise_validation(Code.Tag.NAME_REQUIRED, field="name", status_code=400)
    if EventTag.objects.filter(name__iexact=name).exists():
        raise_validation(Code.Tag.NAME_ALREADY_EXISTS, field="name", status_code=400)
    try:
        with transaction.atomic():
            tag = EventTag.objects.create(name=name)
    except IntegrityError:
        # distinct names can collide on the derived unique slug (e.g. "walk!" → "walk")
        raise_validation(Code.Tag.NAME_ALREADY_EXISTS, field="name", status_code=400)
    audit_log(
        logging.INFO,
        "event_tag_created",
        request,
        target_type="event_tag",
        target_id=str(tag.id),
        details={"name": tag.name, "slug": tag.slug},
    )
    return Status(201, _tag_out(tag))


@router.delete(
    "/event-tags/{tag_id}/",
    response={204: None, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def delete_event_tag(request, tag_id: UUID):
    _require_manage_tags(request, "delete_event_tag", target_id=str(tag_id))
    try:
        tag = EventTag.objects.get(id=tag_id)
    except EventTag.DoesNotExist:
        raise_validation(Code.Tag.NOT_FOUND, status_code=404)
    name = tag.name
    tag.delete()
    audit_log(
        logging.WARNING,
        "event_tag_deleted",
        request,
        target_type="event_tag",
        target_id=str(tag_id),
        details={"name": name},
    )
    return Status(204, None)
