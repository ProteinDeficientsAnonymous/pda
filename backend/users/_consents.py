"""Consent type registry mapping each consent to its User timestamp field."""

from django.db import models
from django.utils import timezone


class ConsentType(models.TextChoices):
    GUIDELINES = "guidelines", "Community guidelines"
    SMS = "sms", "SMS policy"
    CONTACT_PRIVACY = "contact_privacy", "Contact privacy"


CONSENT_FIELDS: dict[ConsentType, str] = {
    ConsentType.GUIDELINES: "guidelines_consent_at",
    ConsentType.SMS: "sms_consent_at",
    ConsentType.CONTACT_PRIVACY: "contact_privacy_consent_at",
}


def stamp_consents(user, consent_types) -> list[str]:
    """Stamp the given consent types, never overwriting existing ones; returns changed field names."""
    now = timezone.now()
    changed: list[str] = []
    for consent_type in consent_types:
        field = CONSENT_FIELDS[ConsentType(consent_type)]
        if getattr(user, field) is None:
            setattr(user, field, now)
            changed.append(field)
    return changed
