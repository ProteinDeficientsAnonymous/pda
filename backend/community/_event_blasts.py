"""Host email-blast endpoint — email everyone who RSVP'd to an event."""

import logging
from uuid import UUID

from config.audit import audit_log
from config.auth import gated_jwt
from config.ratelimit import rate_limit
from ninja import Router, Schema
from ninja.responses import Status
from notifications._email_helpers import send_event_blast_email
from notifications.email_sender import get_email_sender
from pydantic import Field

from community._events import _can_edit_event
from community._shared import ErrorOut
from community._validation import Code, raise_validation
from community.models import Event, EventEmailBlast, RSVPStatus

router = Router()

logger = logging.getLogger("pda.community.event_blasts")

_ALL_RSVP_STATUSES = [status.value for status in RSVPStatus]


class EmailBlastIn(Schema):
    subject: str = Field(..., min_length=1, max_length=150)
    message: str = Field(..., min_length=1, max_length=5000)
    audience: list[str] | None = None


class EmailBlastOut(Schema):
    sent_count: int
    skipped_no_email_count: int
    failed_count: int


def _resolve_audience(audience: list[str] | None) -> list[str]:
    """Validate the requested audience, defaulting to every RSVP status."""
    if not audience:
        return _ALL_RSVP_STATUSES
    valid = set(_ALL_RSVP_STATUSES)
    invalid = [s for s in audience if s not in valid]
    if invalid:
        raise_validation(
            Code.Event.BLAST_INVALID_AUDIENCE,
            field="audience",
            status_code=400,
            invalid=invalid,
            allowed=_ALL_RSVP_STATUSES,
        )
    return [s for s in _ALL_RSVP_STATUSES if s in set(audience)]


def _collect_recipients(event: Event, statuses: list[str]) -> tuple[list, int]:
    """Return (unique (email, display_name) recipients, skipped_no_email_count)."""
    rsvps = event.rsvps.filter(status__in=statuses).select_related("user").order_by("created_at")
    recipients: list[tuple[str, str]] = []
    seen_user_ids: set = set()
    skipped_no_email = 0
    for rsvp in rsvps:
        user = rsvp.user
        if user.id in seen_user_ids:
            continue
        seen_user_ids.add(user.id)
        email = (user.email or "").strip()
        if not email:
            skipped_no_email += 1
            continue
        recipients.append((email, user.display_name or ""))
    return recipients, skipped_no_email


def _send_blast(event: Event, subject: str, message: str, recipients: list) -> int:
    """Send one message per recipient so addresses are never shared. Returns failed_count."""
    sender = get_email_sender()
    failed = 0
    for email, _display_name in recipients:
        try:
            result = send_event_blast_email(
                sender=sender,
                to=email,
                event_title=event.title,
                subject=subject,
                message=message,
            )
        except Exception:  # noqa: BLE001 — one bad send must not abort the batch
            logger.warning("event_blast_send_exception", exc_info=True)
            failed += 1
            continue
        if not result.success:
            failed += 1
    return failed


@router.post(
    "/events/{event_id}/email-blast/",
    response={200: EmailBlastOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut, 429: ErrorOut},
    auth=gated_jwt,
)
@rate_limit(key_func=lambda r, event_id, **_: f"{r.auth.pk}:{event_id}", rate="5/h")
def send_email_blast(request, event_id: UUID, payload: EmailBlastIn):
    """Email everyone who RSVP'd to this event in the chosen audience. Host/co-host only."""
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
            details={"endpoint": "send_email_blast"},
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action="send_email_blast")

    statuses = _resolve_audience(payload.audience)
    recipients, skipped_no_email = _collect_recipients(event, statuses)
    if not recipients:
        raise_validation(
            Code.Event.BLAST_NO_RECIPIENTS,
            status_code=400,
            skipped_no_email_count=skipped_no_email,
        )

    failed_count = _send_blast(event, payload.subject, payload.message, recipients)
    sent_count = len(recipients) - failed_count

    EventEmailBlast.objects.create(
        event=event,
        sender=request.auth,
        subject=payload.subject,
        body=payload.message,
        audience=",".join(statuses),
        recipient_count=sent_count,
        skipped_no_email_count=skipped_no_email,
        failed_count=failed_count,
    )
    audit_log(
        logging.INFO,
        "event_email_blast_sent",
        request,
        target_type="event",
        target_id=str(event_id),
        details={
            "sent_count": sent_count,
            "skipped_no_email_count": skipped_no_email,
            "failed_count": failed_count,
            "audience": statuses,
        },
    )
    return Status(
        200,
        EmailBlastOut(
            sent_count=sent_count,
            skipped_no_email_count=skipped_no_email,
            failed_count=failed_count,
        ),
    )
