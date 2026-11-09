import logging
from datetime import datetime
from uuid import UUID

from community.shared import ErrorOut
from community.validation import Code, raise_validation
from config.audit import AuditTarget, audit_log
from config.auth import gated_jwt
from django.db.models import Q
from ninja import Query, Router, Schema
from ninja.responses import Status
from pydantic import Field
from users.permissions import PermissionKey

from audit.models import AuditLogEntry, AuditTargetType

router = Router()


class AuditLogQuery(Schema):
    target_type: AuditTargetType | None = None
    target_id: str | None = Field(None, max_length=64)
    member_id: UUID | None = Field(
        None,
        description="entries targeting this user, plus any entry whose details.user_id names them",
    )
    actor_id: UUID | None = None
    action: str | None = Field(None, max_length=64)
    since: datetime | None = None
    until: datetime | None = None
    limit: int = Field(50, ge=1, le=100)
    offset: int = Field(0, ge=0)


class AuditLogEntryOut(Schema):
    id: UUID
    created_at: datetime
    action: str
    actor_id: UUID | None
    actor_label: str
    target_type: str
    target_id: str
    details: dict


class AuditLogPageOut(Schema):
    entries: list[AuditLogEntryOut]
    total: int
    next_offset: int | None


def _matching(params: AuditLogQuery):
    exact = {
        "target_type": params.target_type,
        "target_id": params.target_id,
        "actor_id": params.actor_id,
        "action": params.action,
        "created_at__gte": params.since,
        "created_at__lt": params.until,
    }
    qs = AuditLogEntry.objects.filter(**{k: v for k, v in exact.items() if v is not None})
    if params.member_id is not None:
        member = str(params.member_id)
        qs = qs.filter(
            Q(target_type=AuditTargetType.USER, target_id=member) | Q(details__user_id=member)
        )
    return qs


@router.get("/", response={200: AuditLogPageOut, 403: ErrorOut}, auth=gated_jwt)
def list_audit_log(request, params: Query[AuditLogQuery]):
    if not request.auth.has_permission(PermissionKey.VIEW_AUDIT_LOG):
        details = {
            "endpoint": "list_audit_log",
            "required_permission": PermissionKey.VIEW_AUDIT_LOG,
        }
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            persist=False,
            target=AuditTarget(details=details),
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="list_audit_log")

    qs = _matching(params)
    total = qs.count()
    end = params.offset + params.limit
    page = qs.order_by("-created_at", "-id")[params.offset : end]
    return Status(
        200,
        AuditLogPageOut(
            entries=[AuditLogEntryOut.model_validate(e, from_attributes=True) for e in page],
            total=total,
            next_offset=end if end < total else None,
        ),
    )
