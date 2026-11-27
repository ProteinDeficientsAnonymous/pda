import logging
from uuid import UUID

from config.audit import AuditTarget, AuditTargetType, audit_log
from users.permissions import PermissionKey

from community.models import Club, EventType
from community.validation import Code, raise_validation

# Event types that require an explicit permission to tag. Community events need
# none. Maps type → the permission that gates it.
_TYPE_TAG_PERMISSIONS = {
    EventType.OFFICIAL: PermissionKey.TAG_OFFICIAL_EVENT,
    EventType.CLUB: PermissionKey.TAG_CLUB_EVENT,
}


def enforce_type_tag_permission(
    request, event_type: str, endpoint: str, event_id=None, *, club_id: UUID | None = None
) -> None:
    """Raise 403 if the event type requires a tag permission the user lacks (club reps pass for their own club)."""
    required = _TYPE_TAG_PERMISSIONS.get(event_type)
    if required is None or request.auth.has_permission(required):
        return
    if (
        event_type == EventType.CLUB
        and club_id is not None
        and request.auth.rep_clubs.filter(pk=club_id).exists()
    ):
        return
    if event_type == EventType.CLUB and club_id and not Club.objects.filter(pk=club_id).exists():
        raise_validation(Code.Club.NOT_FOUND, field="club_id")
    details = {"endpoint": endpoint, "required_permission": required}
    if event_id is not None:
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            persist=False,
            target=AuditTarget(type=AuditTargetType.EVENT, id=str(event_id), details=details),
        )
    else:
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            persist=False,
            target=AuditTarget(details=details),
        )
    raise_validation(Code.Perm.DENIED, status_code=403, action=required)
