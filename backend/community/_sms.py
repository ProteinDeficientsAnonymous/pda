"""Thin wrapper around the Twilio SMS API.

Loaded lazily so a missing TWILIO_* env var doesn't break Django boot in dev.
Call sites should be prepared for ``RuntimeError("Twilio not configured")``
or ``twilio.base.exceptions.TwilioRestException`` and convert to the right
``Code.TextBlast.*`` validation error.
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from django.conf import settings

if TYPE_CHECKING:
    from twilio.rest import Client


@lru_cache(maxsize=1)
def get_twilio_client() -> Client:
    """Return a cached Twilio Client. Raises ``RuntimeError`` if not configured."""
    if not (settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN):
        raise RuntimeError("Twilio not configured")
    from twilio.rest import Client

    return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


def send_sms(to: str, body: str) -> str:
    """Send an SMS to ``to`` (E.164) with ``body``. Returns the Twilio MessageSid.

    Raises:
        RuntimeError: if Twilio env vars aren't set.
        twilio.base.exceptions.TwilioRestException: on API errors (rate limit,
            invalid recipient, unverified number on trial accounts, etc.).
    """
    if not settings.TWILIO_FROM_NUMBER:
        raise RuntimeError("Twilio not configured")
    client = get_twilio_client()
    message = client.messages.create(
        to=to,
        from_=settings.TWILIO_FROM_NUMBER,
        body=body,
    )
    sid = message.sid
    if sid is None:
        raise RuntimeError("Twilio returned no MessageSid")
    return sid
