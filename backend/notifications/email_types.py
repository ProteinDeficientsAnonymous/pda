"""Shared email types and recipient helpers.

Lives apart from ``email_sender`` (the factory) so concrete senders can import
these without a circular dependency.
"""

import hashlib
from typing import Protocol, runtime_checkable

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from pydantic import BaseModel

# Seeded staging users use this domain; LogOnlyTestDomainSender routes to console.
TEST_EMAIL_DOMAIN = "proteindeficienttestdomain.com"


class SendResult(BaseModel):
    success: bool
    provider_message_id: str | None = None
    error: str | None = None


def mask_recipient(to: str) -> str:
    """Return a non-reversible, low-cardinality token for log correlation.

    Avoids logging the raw recipient address (PII). Lives at the email boundary
    so every sender masks recipients the same way and logs stay correlatable
    without exposing the address. Keep only a short hash prefix.
    """
    digest = hashlib.sha256(to.strip().lower().encode("utf-8")).hexdigest()
    return f"sha256:{digest[:12]}"


def validate_recipient(to: str) -> None:
    """Reject malformed recipients and header-injection attempts.

    Validated at the sender boundary so every email type and every concrete
    sender is protected — not just whichever helper remembers to call it.
    ``validate_email`` already rejects embedded newlines/carriage returns
    (the header-injection vector), so it is the sole check needed.
    """
    try:
        validate_email(to)
    except DjangoValidationError as exc:
        raise ValueError(f"invalid recipient address: {to!r}") from exc


@runtime_checkable
class EmailSender(Protocol):
    def send(self, to: str, subject: str, html: str, text: str) -> SendResult: ...
