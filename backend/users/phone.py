import phonenumbers
from community.validation import Code, raise_validation

# Fallback for bare digits only — a number with an explicit country code is unaffected.
ADMIN_ENTERED_PHONE_REGION = "US"
PUBLIC_FORM_PHONE_REGION = None


def _parse_phone(raw: str, default_region: str | None) -> str | None:
    try:
        parsed = phonenumbers.parse(raw, default_region)
    except phonenumbers.phonenumberutil.NumberParseException:
        return None
    if not phonenumbers.is_valid_number(parsed):
        return None
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def validate_phone(raw: str, default_region: str | None, field: str = "phone_number") -> str:
    """Parse, validate, and return E.164. Raises ValidationException on invalid."""
    canonical = _parse_phone(raw, default_region)
    if canonical is None:
        raise_validation(Code.Phone.INVALID, field=field)
    return canonical


def normalize_phone_number(raw: str) -> str:
    """Best-effort canonicalize to E.164 for save() — never raises on bad legacy data."""
    return _parse_phone(raw, ADMIN_ENTERED_PHONE_REGION) or raw
