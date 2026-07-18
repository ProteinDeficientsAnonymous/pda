import json
import secrets
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from users.models import NonMemberRsvpToken, User

from community.models import (
    Event,
    EventRSVP,
    EventStatus,
    EventType,
    PageVisibility,
    RSVPStatus,
)

E2E_PASSWORD = "e2e-test-pass-123"


def _random_phone() -> str:
    return "+1202555" + str(secrets.randbelow(10_000)).zfill(4)


def _random_event(scenario: str, **overrides) -> Event:
    base = {
        "title": f"E2E {scenario} {secrets.token_hex(4)}",
        "start_datetime": timezone.now() + timedelta(days=30),
        "event_type": EventType.OFFICIAL,
        "visibility": PageVisibility.PUBLIC,
        "status": EventStatus.ACTIVE,
        "rsvp_enabled": True,
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
    user = User.objects.create_user(
        phone_number=phone,
        first_name="E2E",
        last_name="Guest",
        email=f"{phone.lstrip('+')}@example.com",
        is_member=False,
    )
    user.set_unusable_password()
    user.save(update_fields=["password"])
    return user


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
        "user_phone": phone,
        "user_password": E2E_PASSWORD,
        "access_token": _access_token(user),
    }


def _seed_public_new() -> dict:
    event = _random_event("public-new")
    return {"event_id": str(event.id), "event_title": event.title}


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


SCENARIOS = {
    "member": _seed_member,
    "public-new": _seed_public_new,
    "public-returning": _seed_public_returning,
    "comments": _seed_comments,
    "my-rsvps": _seed_my_rsvps,
    "live-updates": _seed_live_updates,
}


class Command(BaseCommand):
    help = "Seed one-off data for a Playwright e2e scenario and print it as JSON."

    def add_arguments(self, parser):
        parser.add_argument("scenario", choices=sorted(SCENARIOS))

    def handle(self, *args, **options):
        scenario = options["scenario"]
        builder = SCENARIOS.get(scenario)
        if builder is None:
            raise CommandError(f"Unknown scenario: {scenario}")
        self.stdout.write(json.dumps(builder()))
