import logging
from uuid import UUID

from config.audit import AuditTarget, AuditTargetType, audit_log
from config.auth import gated_jwt
from ninja import Router
from ninja.responses import Status
from users.permissions import PermissionKey

from community.models import ReserveEntry
from community.reserve.schemas import (
    ReserveEntryIn,
    ReserveEntryOut,
    ReserveEntryPatchIn,
    entry_out,
)
from community.shared import ErrorOut
from community.validation import Code, raise_validation

router = Router()


def _require_edit(request, endpoint: str, target_id: str = "") -> None:
    if request.auth.has_permission(PermissionKey.EDIT_GUIDELINES):
        return
    audit_log(
        logging.WARNING,
        "permission_denied",
        request,
        persist=False,
        target=AuditTarget(
            type=AuditTargetType.RESERVE_ENTRY,
            id=target_id,
            details={"endpoint": endpoint, "required_permission": PermissionKey.EDIT_GUIDELINES},
        ),
    )
    raise_validation(Code.Perm.DENIED, status_code=403, action=endpoint)


def _get_entry(entry_id: UUID) -> ReserveEntry:
    try:
        return ReserveEntry.objects.get(id=entry_id)
    except ReserveEntry.DoesNotExist:
        raise_validation(Code.Reserve.NOT_FOUND, status_code=404)


def _audit(request, action: str, entry: ReserveEntry, level: int = logging.INFO) -> None:
    audit_log(
        level,
        action,
        request,
        target=AuditTarget(
            type=AuditTargetType.RESERVE_ENTRY,
            id=str(entry.id),
            details={"label": entry.label},
        ),
    )


@router.post(
    "/reserve/entries/",
    response={201: ReserveEntryOut, 403: ErrorOut},
    auth=gated_jwt,
)
def create_reserve_entry(request, payload: ReserveEntryIn):
    _require_edit(request, "create_reserve_entry")
    entry = ReserveEntry.objects.create(**payload.model_dump())
    _audit(request, "reserve_entry_created", entry)
    return Status(201, entry_out(entry))


@router.patch(
    "/reserve/entries/{entry_id}/",
    response={200: ReserveEntryOut, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def update_reserve_entry(request, entry_id: UUID, payload: ReserveEntryPatchIn):
    _require_edit(request, "update_reserve_entry", target_id=str(entry_id))
    entry = _get_entry(entry_id)
    updates = payload.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in updates.items():
        setattr(entry, field, value)
    entry.save()
    _audit(request, "reserve_entry_updated", entry)
    return Status(200, entry_out(entry))


@router.delete(
    "/reserve/entries/{entry_id}/",
    response={204: None, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def delete_reserve_entry(request, entry_id: UUID):
    _require_edit(request, "delete_reserve_entry", target_id=str(entry_id))
    entry = _get_entry(entry_id)
    _audit(request, "reserve_entry_deleted", entry, level=logging.WARNING)
    entry.delete()
    return Status(204, None)
