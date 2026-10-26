import logging
from uuid import UUID

from config.audit import AuditTarget, AuditTargetType, audit_log
from django.db import transaction
from django.utils import timezone

from community._validation import Code, raise_validation
from community.models import Event, EventRSVP


def require_permission(request, action: str, *keys: str) -> None:
    if any(request.auth.has_permission(key) for key in keys):
        return
    audit_log(
        logging.WARNING,
        "permission_denied",
        request,
        persist=False,
        target=AuditTarget(type=AuditTargetType.EVENT, id="", details={"action": action}),
    )
    raise_validation(Code.Perm.DENIED, status_code=403, action=action)


def upsert_attendance_rsvps(event: Event, marks: dict[UUID, tuple[str, str]]) -> set[UUID]:
    """Bulk upsert rsvps, mirroring EventRSVP.save() since bulk writes bypass it.

    param(marks): user id -> (rsvp status, attendance); statuses are never waitlisted
    return(set[UUID]): user ids that already had an rsvp
    """
    now = timezone.now()
    with transaction.atomic():
        Event.objects.select_for_update().only("id").get(pk=event.pk)
        existing = list(
            EventRSVP.objects.select_for_update().filter(event=event, user_id__in=marks)
        )
        for rsvp in existing:
            status, rsvp.attendance = marks[rsvp.user_id]
            if status != rsvp.status:
                rsvp.status = status
                rsvp.status_changed_at = now
            rsvp.waitlist_position = None
            rsvp.updated_at = now
        EventRSVP.objects.bulk_update(
            existing,
            ["status", "attendance", "status_changed_at", "waitlist_position", "updated_at"],
        )
        existing_ids = {r.user_id for r in existing}
        EventRSVP.objects.bulk_create(
            EventRSVP(event=event, user_id=uid, status=s, attendance=a, status_changed_at=now)
            for uid, (s, a) in marks.items()
            if uid not in existing_ids
        )
    return existing_ids
