"""User creation and validation helpers."""

import secrets
import string
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

import phonenumbers
from community._shared import validate_display_name
from community._validation import Code, raise_validation

from users._name_parsing import parse_display_name
from users.models import MagicLoginToken, User
from users.roles import Role


@dataclass
class ConsentTimestamps:
    """Consent timestamps captured on a JoinRequest before user creation."""

    guidelines_consent_at: datetime | None = None
    sms_consent_at: datetime | None = None


def _generate_temp_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


class NamePatchPayload(Protocol):
    first_name: str | None
    last_name: str | None
    display_name: str | None


def _resolve_name_fields(user: User, payload: NamePatchPayload) -> bool:
    """Apply first/last name from a patch payload to user (in memory).

    first/last win when provided; a bare legacy display_name is parsed as a
    fallback. Returns True if any name field was set.
    """
    if payload.first_name is not None or payload.last_name is not None:
        if payload.first_name is not None:
            validate_display_name(payload.first_name, field="first_name")
            user.first_name = payload.first_name.strip()
        if payload.last_name is not None:
            if payload.last_name.strip():
                validate_display_name(payload.last_name, field="last_name")
            user.last_name = payload.last_name.strip()
        return True
    if payload.display_name is not None:
        validate_display_name(payload.display_name)
        user.first_name, user.last_name = parse_display_name(payload.display_name.strip())
        return True
    return False


def _create_magic_token(user: User, *, requires_password_reset: bool = False) -> str:
    """Create a one-time magic login token. Returns the token UUID string.

    Pass requires_password_reset=True for self-service login links so consuming
    the token forces a password reset (admin onboarding links leave it False).
    """
    magic = MagicLoginToken.create_for_user(user, requires_password_reset=requires_password_reset)
    return str(magic.token)


def _is_last_admin(user: User) -> bool:
    try:
        admin_role = Role.objects.get(name="admin", is_default=True)
    except Role.DoesNotExist:
        return False
    if not user.roles.filter(pk=admin_role.pk).exists():
        return False
    return admin_role.users.filter(archived_at__isnull=True).count() <= 1


def _is_admin(user: User) -> bool:
    """True if the user holds the built-in admin role."""
    return user.roles.filter(name="admin", is_default=True).exists()


def visible_name(target: User, viewer: User | None) -> tuple[str, str]:
    """Return (last_name, full_name) as they should appear to viewer.

    Admins and the target themself always see the full name. Everyone else
    sees first-name-only when target.hide_last_name is set. A None viewer
    (anonymous/optional-auth) is treated as non-admin, non-self.
    """
    if viewer is not None and (target.id == viewer.id or _is_admin(viewer)):
        return target.last_name, target.full_name
    if target.hide_last_name:
        return "", target.first_name.strip()
    return target.last_name, target.full_name


def visible_display_name(target: User, viewer: User | None) -> str:
    """Member-facing name honoring hide_last_name, falling back to phone.

    viewer=None (anonymous/optional-auth) is treated as non-admin, non-self.
    When the last name is hidden we can only show first_name — display_name is
    the concatenated full name and would leak the last name. When not hidden we
    prefer full_name, then the display_name column (covers legacy accounts whose
    name lives only there). The phone fallback is suppressed when show_phone is
    false so a nameless member's private number is never surfaced as their name.
    """
    is_privileged = viewer is not None and (target.id == viewer.id or _is_admin(viewer))
    if target.hide_last_name and not is_privileged:
        name = target.first_name.strip()
    else:
        name = target.full_name or target.display_name or ""
    if name:
        return name
    return target.phone_number if target.show_phone else "member"


def _normalize_email(raw: str | None) -> str | None:
    """Lowercase + strip an email. Returns None for blank input.

    Centralized so server-side enforcement is consistent across endpoints.
    Frontend should NOT rely on this — normalize there too.
    """
    if not raw:
        return None
    cleaned = raw.strip().lower()
    return cleaned or None


def _check_and_set_email(
    user: User,
    raw: str | None,
    *,
    exclude_pk: uuid.UUID | str | None = None,
) -> None:
    """Normalize email, enforce uniqueness, and assign to user.email.

    Raises ValidationException(409, "email.already_exists") on collision.
    Passes the normalized value (possibly None) through to ``user.email``.

    Pass ``exclude_pk`` for the self-update case so users can re-submit
    their own current email without a false collision.
    """
    normalized = _normalize_email(raw)
    if normalized:
        qs = User.objects.filter(email=normalized)
        if exclude_pk is not None:
            qs = qs.exclude(pk=exclude_pk)
        if qs.exists():
            raise_validation(Code.Email.ALREADY_EXISTS, field="email", status_code=409)
    user.email = normalized


def _validate_phone(raw: str, field: str = "phone_number") -> str:
    """Parse, validate, and return E.164. Raises ValidationException on invalid.

    Defaults to US region so bare 10-digit numbers are accepted.
    Numbers with an explicit country code (e.g. +44...) are unaffected.
    """
    try:
        parsed = phonenumbers.parse(raw, "US")
    except phonenumbers.phonenumberutil.NumberParseException:
        raise_validation(Code.Phone.INVALID, field=field)
    if not phonenumbers.is_valid_number(parsed):
        raise_validation(Code.Phone.INVALID, field=field)
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def _guard_admin_role_grant(role_id: str | None, requesting_user: User) -> None:
    """Block assigning the built-in admin role unless the requester is an admin.

    Prevents privilege escalation when a user holds CREATE_USER but is not
    themselves an admin. No-op for any non-admin role (or no role).
    """
    if not role_id:
        return
    admin_role = Role.objects.filter(name="admin", is_default=True).first()
    if admin_role and str(role_id) == str(admin_role.pk) and not _is_admin(requesting_user):
        raise_validation(Code.Role.CANNOT_GRANT_ADMIN, field="role_id", status_code=403)


def _create_user_with_role(  # noqa: PLR0913
    phone: str,
    first_name: str,
    last_name: str,
    email: str | None,
    role_id: str | None,
    *,
    requesting_user: User,
    consent: ConsentTimestamps | None = None,
) -> tuple[User, str]:
    """Validate phone, create user, assign role. Returns (user, magic_link_token).

    Raises ValidationException on validation failure (bad phone, duplicate, bad role).
    Assigning the built-in admin role is only permitted when ``requesting_user``
    is themselves an admin (prevents escalation under CREATE_USER alone).

    Pass ``consent`` when the user was created from a join request that already
    captured consent — otherwise it defaults to None (e.g. admin-created users
    who have no prior consent record).
    """
    validated_phone = _validate_phone(phone)
    if User.objects.filter(phone_number=validated_phone).exists():
        raise_validation(Code.Phone.ALREADY_EXISTS, field="phone_number", status_code=409)
    normalized_email = _normalize_email(email)
    if normalized_email and User.objects.filter(email=normalized_email).exists():
        raise_validation(Code.Email.ALREADY_EXISTS, field="email", status_code=409)
    _guard_admin_role_grant(role_id, requesting_user)
    user = User.objects.create_user(
        phone_number=validated_phone,
        first_name=first_name,
        last_name=last_name,
        email=normalized_email,
        is_member=True,
        needs_onboarding=True,
        guidelines_consent_at=consent.guidelines_consent_at if consent else None,
        sms_consent_at=consent.sms_consent_at if consent else None,
    )
    user.set_unusable_password()
    user.save(update_fields=["password"])
    try:
        if role_id:
            role = Role.objects.get(pk=role_id)
            user.roles.add(role)
        else:
            member_role = Role.objects.filter(name="member", is_default=True).first()
            if member_role:
                user.roles.add(member_role)
    except Role.DoesNotExist:
        user.delete()
        raise_validation(Code.Role.NOT_FOUND, field="role_id", status_code=404)
    magic_token = _create_magic_token(user)
    return user, magic_token


def _validate_admin_role_change(user: User, requesting_user: User, new_roles: list[Role]) -> None:
    """Raise ValidationException if an admin role change is invalid.

    Guards both directions:
    - Removing admin from oneself or the last admin is blocked.
    - Granting the built-in admin role is blocked unless the requester is
      themselves an admin (prevents privilege escalation via MANAGE_USERS).
    """
    admin_role = Role.objects.filter(name="admin", is_default=True).first()
    if not admin_role:
        return

    is_self = str(user.pk) == str(requesting_user.pk)
    is_current_admin = user.roles.filter(pk=admin_role.pk).exists()
    removing_admin = admin_role not in new_roles
    adding_admin = admin_role in new_roles and not is_current_admin

    if adding_admin and not _is_admin(requesting_user):
        raise_validation(Code.Role.CANNOT_GRANT_ADMIN, status_code=403)

    if is_self and is_current_admin and removing_admin:
        raise_validation(Code.Role.CANNOT_REMOVE_OWN_ADMIN, status_code=400)

    if _is_last_admin(user) and removing_admin:
        raise_validation(Code.Role.CANNOT_REMOVE_LAST_ADMIN, status_code=400)


def _validate_member_role_required(new_roles: list[Role]) -> None:
    """Raise ValidationException if the new role set is missing the built-in member role."""
    member_role = Role.objects.filter(name="member", is_default=True).first()
    if not member_role:
        return
    if member_role not in new_roles:
        raise_validation(Code.Role.MEMBER_ROLE_REQUIRED, status_code=400)
