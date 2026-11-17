import secrets
from datetime import UTC, datetime, timedelta

from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from users.models import MembershipStatus, User
from users.roles import Role

from community.models import Event, EventStatus, EventType, PageVisibility

E2E_PASSWORD = "e2e-test-pass-123"
_CONSENT_AT = datetime(2020, 1, 1, tzinfo=UTC)


def random_phone() -> str:
    # the 555 pool is only 10k numbers, so a blind pick can collide with an existing user
    while True:
        phone = "+1202555" + str(secrets.randbelow(10_000)).zfill(4)
        if not User.objects.filter(phone_number=phone).exists():
            return phone


def random_event(scenario: str, **overrides) -> Event:
    base = {
        "title": f"E2E {scenario} {secrets.token_hex(4)}",
        "start_datetime": timezone.now() + timedelta(days=30),
        "event_type": EventType.OFFICIAL,
        "visibility": PageVisibility.PUBLIC,
        "status": EventStatus.ACTIVE,
        "rsvp_enabled": True,
        "location": f"secret loft {secrets.token_hex(3)}",
    }
    base.update(overrides)
    return Event.objects.create(**base)


def member_user(phone: str) -> User:
    user = User.objects.create_user(
        phone_number=phone,
        first_name="E2E",
        last_name="Member",
        email=f"{phone.lstrip('+')}@example.com",
        membership_status=MembershipStatus.ACTIVE_MEMBER,
        has_seen_veganniversary=True,
        password=E2E_PASSWORD,
    )
    return user


def browser_user(permissions: list[str] | None = None) -> User:
    user = member_user(random_phone())
    user.guidelines_consent_at = _CONSENT_AT
    user.sms_consent_at = _CONSENT_AT
    user.contact_privacy_consent_at = _CONSENT_AT
    user.save(
        update_fields=["guidelines_consent_at", "sms_consent_at", "contact_privacy_consent_at"]
    )
    if permissions:
        role = Role.objects.create(name=f"e2e-role-{secrets.token_hex(4)}", permissions=permissions)
        user.roles.add(role)
    return user


def non_member_user(phone: str) -> User:
    # create_user with no password calls set_password(None) → unusable password.
    return User.objects.create_user(
        phone_number=phone,
        first_name="E2E",
        last_name="Guest",
        email=f"{phone.lstrip('+')}@example.com",
        membership_status=MembershipStatus.NONE,
    )


def issue_access_token(user: User) -> str:
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token)  # type: ignore[attr-defined]
