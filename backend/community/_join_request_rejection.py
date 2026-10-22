import logging
import re
from typing import NamedTuple

from notifications._email_helpers import send_join_rejection_email
from notifications.email_sender import get_email_sender

from community._field_limits import FieldLimit
from community._rejection_email import REASON_TEXT_FIELDS
from community._shared import render_template_placeholders
from community._validation import Code, raise_validation
from community.models import JoinRequest, RejectionEmailTemplate, RejectionReason


class Rejection(NamedTuple):
    reason: str = ""
    note: str = ""


def validate_rejection(reason: str, note: str) -> Rejection:
    """Normalize a vetter's optional rejection reason; the note is kept only for OTHER."""
    if not reason:
        return Rejection()
    if reason not in RejectionReason.values:
        raise_validation(
            Code.JoinRequest.INVALID_REJECTION_REASON,
            field="rejection_reason",
            allowed=RejectionReason.values,
        )
    if reason != RejectionReason.OTHER:
        return Rejection(reason=reason)
    note = note.strip()
    if not note:
        raise_validation(Code.JoinRequest.REJECTION_NOTE_REQUIRED, field="rejection_note")
    if len(note) > FieldLimit.REJECTION_NOTE:
        raise_validation(
            Code.JoinRequest.REJECTION_NOTE_TOO_LONG,
            field="rejection_note",
            max_length=FieldLimit.REJECTION_NOTE,
        )
    return Rejection(reason=reason, note=note)


def _reason_text(template: RejectionEmailTemplate, join_request: JoinRequest) -> str:
    if join_request.rejection_reason == RejectionReason.OTHER:
        return join_request.rejection_note
    field = REASON_TEXT_FIELDS.get(join_request.rejection_reason)
    return getattr(template, field) if field else ""


def render_rejection_body(join_request: JoinRequest) -> str:
    template = RejectionEmailTemplate.get()
    body = render_template_placeholders(
        template.body,
        {
            "FIRST_NAME": join_request.first_name,
            "REASON": _reason_text(template, join_request),
        },
    )
    # An empty ${REASON} would otherwise leave a run of blank lines behind.
    return re.sub(r"\n{3,}", "\n\n", body).strip()


def send_join_rejection(join_request: JoinRequest) -> None:
    """Best-effort rejection email. A send failure must not roll back the rejection."""
    if not join_request.email:
        return
    try:
        send_join_rejection_email(
            sender=get_email_sender(),
            to=join_request.email,
            display_name=join_request.first_name,
            message_body=render_rejection_body(join_request),
        )
    except Exception:
        logging.getLogger(__name__).warning("join rejection email failed", exc_info=True)
