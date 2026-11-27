import logging
from datetime import datetime

from community.shared import ErrorOut
from community.validation import Code, raise_validation
from config.audit import AuditTarget, AuditTargetType, audit_log
from config.auth import gated_jwt
from config.ratelimit import rate_limit
from ninja import Router, Schema
from ninja.responses import Status
from pydantic import Field
from users.permissions import PermissionKey

from notifications.member_blasts.service import (
    collect_recipients,
    render_blast,
    send_member_blast,
    send_test_blast,
)
from notifications.models import MemberEmailBlast

router = Router()

_ERRORS = {400: ErrorOut, 403: ErrorOut, 429: ErrorOut}


class BlastIn(Schema):
    subject: str = Field(..., min_length=1, max_length=150)
    body_html: str = Field(..., min_length=1, max_length=100_000)


class BlastPreviewOut(Schema):
    html: str
    text: str
    recipient_count: int
    skipped_count: int


class BlastTestOut(Schema):
    sent: bool


class BlastOut(Schema):
    id: str
    status: str
    sent_count: int
    failed_count: int
    unknown_count: int
    skipped_count: int
    subject: str
    sender_id: str | None
    created_at: datetime


def _blast_out(blast: MemberEmailBlast) -> BlastOut:
    return BlastOut(
        id=str(blast.id),
        status=blast.status,
        sent_count=blast.recipient_count - blast.failed_count - blast.unknown_count,
        failed_count=blast.failed_count,
        unknown_count=blast.unknown_count,
        skipped_count=blast.skipped_count,
        subject=blast.subject,
        sender_id=str(blast.sender_id) if blast.sender_id else None,
        created_at=blast.created_at,
    )


def _require_permission(request, endpoint: str) -> None:
    if request.auth.has_permission(PermissionKey.SEND_EMAIL_BLAST):
        return
    audit_log(
        logging.WARNING,
        "permission_denied",
        request,
        persist=False,
        target=AuditTarget(type=AuditTargetType.MEMBER_EMAIL_BLAST, details={"endpoint": endpoint}),
    )
    raise_validation(Code.Perm.DENIED, status_code=403, action=endpoint)


@router.post("preview/", response={200: BlastPreviewOut, **_ERRORS}, auth=gated_jwt)
def preview_blast(request, payload: BlastIn):
    _require_permission(request, "preview_blast")
    rendered = render_blast(payload.subject, payload.body_html)
    emails, skipped = collect_recipients()
    return Status(
        200,
        BlastPreviewOut(
            html=rendered.html,
            text=rendered.text,
            recipient_count=len(emails),
            skipped_count=skipped,
        ),
    )


@router.post("test/", response={200: BlastTestOut, **_ERRORS}, auth=gated_jwt)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="10/h")
def send_test(request, payload: BlastIn):
    _require_permission(request, "send_test")
    result = send_test_blast(
        user=request.auth, subject=payload.subject, body_html=payload.body_html
    )
    return Status(200, BlastTestOut(sent=result.accepted > 0))


@router.post("", response={200: BlastOut, **_ERRORS}, auth=gated_jwt)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="3/h")
def send_blast(request, payload: BlastIn):
    _require_permission(request, "send_blast")
    blast = send_member_blast(
        sender=request.auth, subject=payload.subject, body_html=payload.body_html
    )
    out = _blast_out(blast)
    audit_log(
        logging.INFO,
        "member_email_blast_sent",
        request,
        target=AuditTarget(
            type=AuditTargetType.MEMBER_EMAIL_BLAST,
            id=out.id,
            details={
                "status": out.status,
                "sent_count": out.sent_count,
                "failed_count": out.failed_count,
                "unknown_count": out.unknown_count,
                "skipped_count": out.skipped_count,
            },
        ),
    )
    return Status(200, out)


@router.get("", response={200: list[BlastOut], **_ERRORS}, auth=gated_jwt)
def list_blasts(request):
    _require_permission(request, "list_blasts")
    return Status(
        200, [_blast_out(b) for b in MemberEmailBlast.objects.order_by("-created_at")[:20]]
    )
