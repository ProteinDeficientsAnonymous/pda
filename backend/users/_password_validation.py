"""Shared password-strength validation."""

import re


def validate_password(password: str) -> list[str]:
    """Return a list of rule violations (empty list = valid)."""
    errors = []
    if len(password) < 12:
        errors.append("must be at least 12 characters")
    if not re.search(r"[A-Z]", password):
        errors.append("must include an uppercase letter")
    if not re.search(r"[0-9]", password):
        errors.append("must include a number")
    if not re.search(r"[^A-Za-z0-9]", password):
        errors.append("must include a special character")
    return errors
