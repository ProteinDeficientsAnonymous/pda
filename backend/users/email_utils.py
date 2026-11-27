def normalize_email(raw: str | None) -> str | None:
    """Lowercase + strip an email. Returns None for blank input."""
    if not raw:
        return None
    cleaned = raw.strip().lower()
    return cleaned or None
