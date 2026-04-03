"""User creation and validation helpers."""

import secrets
import string

import phonenumbers

from users.models import MagicLoginToken, User
from users.roles import Role


def _generate_temp_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _create_magic_token(user: User) -> str:
    """Create a one-time magic login token. Returns the token UUID string."""
    magic = MagicLoginToken.create_for_user(user)
    return str(magic.token)


def _is_last_admin(user: User) -> bool:
    try:
        admin_role = Role.objects.get(name="admin", is_default=True)
    except Role.DoesNotExist:
        return False
    if not user.roles.filter(pk=admin_role.pk).exists():
        return False
    return admin_role.users.count() <= 1


def _validate_phone(raw: str) -> str:
    """Parse, validate, and return E.164. Raises ValueError on invalid.

    Defaults to US region so bare 10-digit numbers are accepted.
    Numbers with an explicit country code (e.g. +44...) are unaffected.
    """
    try:
        parsed = phonenumbers.parse(raw, "US")
    except phonenumbers.phonenumberutil.NumberParseException as e:
        raise ValueError(str(e)) from e
    if not phonenumbers.is_valid_number(parsed):
        raise ValueError(f"Invalid phone number: {raw}")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def _create_user_with_role(
    phone: str,
    display_name: str,
    email: str | None,
    role_id: str | None,
    *,
    needs_onboarding: bool = True,
) -> tuple[User, str]:
    """Validate phone, create user, assign role. Returns (user, magic_link_token).

    Raises ValueError on validation failure (bad phone, duplicate, bad role).
    """
    validated_phone = _validate_phone(phone)
    if User.objects.filter(phone_number=validated_phone).exists():
        raise ValueError("A user with that phone number already exists.")
    user = User.objects.create_user(
        phone_number=validated_phone,
        display_name=display_name,
        email=email,
        needs_onboarding=needs_onboarding,
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
        raise ValueError("Role not found.")
    magic_token = _create_magic_token(user)
    return user, magic_token


def _validate_admin_role_change(
    user: User, requesting_user_pk, new_roles: list[Role]
) -> str | None:
    """Return error message if admin role change is invalid, None if OK."""
    admin_role = Role.objects.filter(name="admin", is_default=True).first()
    if not admin_role:
        return None

    is_self = str(user.pk) == str(requesting_user_pk)
    is_current_admin = user.roles.filter(pk=admin_role.pk).exists()
    removing_admin = admin_role not in new_roles

    if is_self and is_current_admin and removing_admin:
        return "You cannot remove your own admin role."

    if _is_last_admin(user) and removing_admin:
        return "Cannot remove admin from the last admin."

    return None
