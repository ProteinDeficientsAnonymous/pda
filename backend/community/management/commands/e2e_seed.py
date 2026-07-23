import json
import secrets
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from users.models import NonMemberRsvpToken, Role, User
from users.permissions import PermissionKey

from community.models import (
    AttendanceStatus,
    Event,
    EventRSVP,
    EventStatus,
    EventType,
    FeatureFlag,
    FeatureFlagState,
    PageVisibility,
    RSVPStatus,
)

E2E_PASSWORD = "e2e-test-pass-123"


def _random_phone() -> str:
    while True:
        phone = "+1202555" + str(secrets.randbelow(10_000)).zfill(4)
        if not User.objects.filter(phone_number=phone).exists():
            return phone


def _random_event(scenario: str, **overrides) -> Event:
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


def _member_user(phone: str) -> User:
    user = User.objects.create_user(
        phone_number=phone,
        first_name="E2E",
        last_name="Member",
        email=f"{phone.lstrip('+')}@example.com",
        is_member=True,
        password=E2E_PASSWORD,
    )
    return user


def _non_member_user(phone: str) -> User:
    # create_user with no password calls set_password(None) → unusable password.
    return User.objects.create_user(
        phone_number=phone,
        first_name="E2E",
        last_name="Guest",
        email=f"{phone.lstrip('+')}@example.com",
        is_member=False,
    )


def _access_token(user: User) -> str:
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token)  # type: ignore[attr-defined]


def _seed_member() -> dict:
    event = _random_event("member")
    phone = _random_phone()
    user = _member_user(phone)
    return {
        "event_id": str(event.id),
        "event_title": event.title,
        "event_location": event.location,
        "user_phone": phone,
        "user_password": E2E_PASSWORD,
        "access_token": _access_token(user),
    }


def _seed_public_new() -> dict:
    event = _random_event("public-new")
    return {
        "event_id": str(event.id),
        "event_title": event.title,
        "event_location": event.location,
    }


def _seed_public_returning() -> dict:
    event = _random_event("public-returning")
    phone = _random_phone()
    user = _non_member_user(phone)
    EventRSVP.objects.create(event=event, user=user, status=RSVPStatus.ATTENDING)
    token = NonMemberRsvpToken.issue_or_extend(user)
    return {
        "event_id": str(event.id),
        "event_title": event.title,
        "user_phone": phone,
        "rsvp_token": token.token,
    }


def _seed_public_recognized() -> dict:
    # non-member with an email, no token on this device
    prior_event = _random_event("public-recognized-prior")
    target_event = _random_event("public-recognized")
    phone = _random_phone()
    user = _non_member_user(phone)
    EventRSVP.objects.create(event=prior_event, user=user, status=RSVPStatus.ATTENDING)
    return {
        "event_id": str(target_event.id),
        "event_title": target_event.title,
        "user_phone": phone,
    }


def _seed_comments() -> dict:
    event = _random_event("comments")
    phone = _random_phone()
    user = _non_member_user(phone)
    EventRSVP.objects.create(event=event, user=user, status=RSVPStatus.ATTENDING)
    token = NonMemberRsvpToken.issue_or_extend(user)
    return {"event_id": str(event.id), "event_title": event.title, "rsvp_token": token.token}


def _seed_my_rsvps() -> dict:
    event = _random_event("my-rsvps")
    phone = _random_phone()
    user = _non_member_user(phone)
    EventRSVP.objects.create(event=event, user=user, status=RSVPStatus.ATTENDING)
    token = NonMemberRsvpToken.issue_or_extend(user)
    return {"event_id": str(event.id), "event_title": event.title, "rsvp_token": token.token}


def _seed_live_updates() -> dict:
    event = _random_event("live-updates")
    phone_a, phone_b = _random_phone(), _random_phone()
    _member_user(phone_a)
    _member_user(phone_b)
    return {
        "event_id": str(event.id),
        "event_title": event.title,
        "user_a_phone": phone_a,
        "user_a_password": E2E_PASSWORD,
        "user_b_phone": phone_b,
        "user_b_password": E2E_PASSWORD,
    }


def _admin_user(phone: str, permissions: list[str]) -> User:
    user = _member_user(phone)
    role = Role.objects.create(name=f"e2e-role-{secrets.token_hex(4)}", permissions=permissions)
    user.roles.add(role)
    return user


def _seed_attendance_report() -> dict:
    FeatureFlagState.objects.update_or_create(
        key=FeatureFlag.HOST_ATTENDANCE_REPORT, defaults={"enabled": True}
    )
    host_phone = _random_phone()
    host = _admin_user(host_phone, [PermissionKey.MANAGE_EVENTS])
    event = _random_event(
        "attendance-report",
        start_datetime=timezone.now() - timedelta(days=2),
        end_datetime=timezone.now() - timedelta(days=2) + timedelta(hours=2),
        created_by=host,
    )

    attended = _member_user(_random_phone())
    no_show = _member_user(_random_phone())
    canceled = _non_member_user(_random_phone())
    EventRSVP.objects.create(
        event=event,
        user=attended,
        status=RSVPStatus.ATTENDING,
        attendance=AttendanceStatus.ATTENDED,
    )
    EventRSVP.objects.create(
        event=event, user=no_show, status=RSVPStatus.ATTENDING, attendance=AttendanceStatus.NO_SHOW
    )
    EventRSVP.objects.create(
        event=event,
        user=canceled,
        status=RSVPStatus.CANT_GO,
        cancelled_at=timezone.now() - timedelta(days=3),
    )

    return {
        "event_id": str(event.id),
        "event_title": event.title,
        "host_phone": host_phone,
        "host_password": E2E_PASSWORD,
    }


def _seed_attendance_analytics() -> dict:
    FeatureFlagState.objects.update_or_create(
        key=FeatureFlag.ADMIN_ATTENDANCE_ANALYTICS, defaults={"enabled": True}
    )
    admin_phone = _random_phone()
    _admin_user(admin_phone, [PermissionKey.MANAGE_EVENTS, PermissionKey.MANAGE_USERS])

    recent_event = _random_event(
        "analytics-recent",
        event_type=EventType.OFFICIAL,
        start_datetime=timezone.now() - timedelta(days=10),
    )
    stale_event = _random_event(
        "analytics-stale",
        event_type=EventType.CLUB,
        start_datetime=timezone.now() - timedelta(days=400),
    )

    suffix = secrets.token_hex(4)
    compliant_first_name = f"Zoe{suffix}"
    at_risk_first_name = f"Yara{suffix}"

    compliant = _member_user(_random_phone())
    compliant.first_name = compliant_first_name
    compliant.save(update_fields=["first_name"])
    at_risk = _member_user(_random_phone())
    at_risk.first_name = at_risk_first_name
    at_risk.save(update_fields=["first_name"])

    EventRSVP.objects.create(
        event=recent_event,
        user=compliant,
        status=RSVPStatus.ATTENDING,
        attendance=AttendanceStatus.ATTENDED,
    )
    EventRSVP.objects.create(
        event=stale_event,
        user=at_risk,
        status=RSVPStatus.ATTENDING,
        attendance=AttendanceStatus.ATTENDED,
    )

    return {
        "admin_phone": admin_phone,
        "admin_password": E2E_PASSWORD,
        "compliant_name": f"{compliant_first_name} member".lower(),
        "at_risk_name": f"{at_risk_first_name} member".lower(),
    }


SCENARIOS = {
    "member": _seed_member,
    "public-new": _seed_public_new,
    "public-recognized": _seed_public_recognized,
    "public-returning": _seed_public_returning,
    "comments": _seed_comments,
    "my-rsvps": _seed_my_rsvps,
    "live-updates": _seed_live_updates,
    "attendance-report": _seed_attendance_report,
    "attendance-analytics": _seed_attendance_analytics,
}


class Command(BaseCommand):
    help = "Seed one-off data for a Playwright e2e scenario and print it as JSON."

    def add_arguments(self, parser):
        parser.add_argument("scenario", choices=sorted(SCENARIOS))

    def handle(self, *args, **options):
        # argparse choices= already rejects any unknown scenario before handle runs.
        self.stdout.write(json.dumps(SCENARIOS[options["scenario"]]()))
