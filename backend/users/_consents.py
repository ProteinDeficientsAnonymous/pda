"""Consent type registry — the single source of truth for the kinds of consent
the app collects and which User timestamp field records each one.

Adding a new consent type (e.g. an email policy) is a two-step change: add a
``ConsentType`` member and a ``CONSENT_FIELDS`` entry pointing at a nullable
``*_consent_at`` field on User. The accept-consents endpoint and onboarding both
stamp consents through this registry, so neither needs per-type branching.

Semantics shared by every consent type:
  - A null timestamp means "not yet consented" (surfaced on /me/ as
    needs_<type>_consent).
  - Stamping records the consent and NEVER overwrites an existing timestamp.

Note the asymmetry that lives OUTSIDE this registry: only GUIDELINES is a hard
login gate (see config.auth.GatedJWTAuth, keyed directly on
guidelines_consent_at). SMS is recorded but never locks a user out. New consent
types default to "recorded, not gated" unless the gate is taught about them.
"""

from django.db import models
from django.utils import timezone


class ConsentType(models.TextChoices):
    GUIDELINES = "guidelines", "Community guidelines"
    SMS = "sms", "SMS policy"


# consent type -> the nullable User datetime field that records it.
CONSENT_FIELDS: dict[ConsentType, str] = {
    ConsentType.GUIDELINES: "guidelines_consent_at",
    ConsentType.SMS: "sms_consent_at",
}


def stamp_consents(user, consent_types) -> list[str]:
    """Stamp the given consent types on the user, never overwriting existing ones.

    Returns the list of User field names actually changed, so the caller can
    pass them to ``save(update_fields=...)`` and emit an accurate audit record.
    """
    now = timezone.now()
    changed: list[str] = []
    for consent_type in consent_types:
        field = CONSENT_FIELDS[ConsentType(consent_type)]
        if getattr(user, field) is None:
            setattr(user, field, now)
            changed.append(field)
    return changed
