import json
import secrets
from datetime import UTC, datetime, timedelta

from django.core.cache import caches
from django.core.management.base import BaseCommand
from django.db import connection
from django.template.loader import render_to_string
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from users.models import NonMemberRsvpToken, User
from users.roles import Role

from community.models import (
    DocFolder,
    Document,
    Event,
    EventRSVP,
    EventStatus,
    EventType,
    JoinFormQuestion,
    JoinRequest,
    PageVisibility,
    RSVPStatus,
    Survey,
)
from community.models.feature_flag import FeatureFlagState

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
        has_seen_veganniversary=True,
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
    user_b = _member_user(phone_b)
    EventRSVP.objects.create(event=event, user=user_b, status=RSVPStatus.ATTENDING)
    return {
        "event_id": str(event.id),
        "event_title": event.title,
        "user_a_phone": phone_a,
        "user_a_password": E2E_PASSWORD,
        "user_b_phone": phone_b,
        "user_b_password": E2E_PASSWORD,
    }


_SCREEN_PHONES = (
    "+17025550002",
    "+17025550003",
    "+17025550004",
    "+17025550005",
    "+17025550006",
    "+17025550008",
    "+17025550009",
)
_SCREEN_EMAILS = (
    "member@pda.test",
    "jamie@pda.test",
    "river@example.com",
    "ada@pda.test",
    "remy@example.com",
    "casey@example.com",
    "sam@example.com",
)
_POTLUCK_AT = datetime(2026, 10, 9, 22, 0, tzinfo=UTC)
_HIKE_AT = datetime(2026, 9, 4, 22, 0, tzinfo=UTC)
_PICNIC_AT = datetime(2026, 11, 6, 22, 0, tzinfo=UTC)
_RECORD_AT = datetime(2026, 6, 1, 18, 0, tzinfo=UTC)
_SCREEN_SLUGS = ("potluck", "hike", "picnic")
_CONSENT_AT = datetime(2020, 1, 1, tzinfo=UTC)


def _screen_user(**fields) -> User:
    user = User.objects.create_user(password=E2E_PASSWORD, is_member=True, **fields)
    user.guidelines_consent_at = _CONSENT_AT
    user.sms_consent_at = _CONSENT_AT
    user.contact_privacy_consent_at = _CONSENT_AT
    user.save(
        update_fields=[
            "guidelines_consent_at",
            "sms_consent_at",
            "contact_privacy_consent_at",
        ]
    )
    return user


def _seed_member_screens() -> dict:
    # Login is capped at 5/minute per IP. Pytest's database has no cache table.
    if "django_cache" in connection.introspection.table_names():
        caches["ratelimit"].clear()
    Event.objects.filter(slug__in=_SCREEN_SLUGS).delete()
    Survey.objects.filter(slug="potluck-feedback").delete()
    DocFolder.objects.filter(name="guides").delete()
    JoinRequest.objects.filter(phone_number="+17025550007").delete()
    JoinFormQuestion.objects.filter(label="how did you hear about us?").delete()
    User.objects.filter(phone_number__in=_SCREEN_PHONES).delete()
    User.objects.filter(email__in=_SCREEN_EMAILS).delete()
    seed = _screen_user(
        phone_number="+17025550002",
        first_name="Seed",
        last_name="Member",
        email="member@pda.test",
        bio="vegan six years, big into potlucks and mutual aid.",
        birthday_month=6,
        birthday_day=15,
        birthday_year=1990,
        veganniversary_month=6,
        veganniversary_year=2020,
        has_seen_veganniversary=True,
    )
    jamie = _screen_user(
        phone_number="+17025550003",
        first_name="Jamie",
        last_name="Okafor",
        email="jamie@pda.test",
        bio="food not bombs volunteer. cook, eat, organize.",
        birthday_month=3,
        birthday_day=2,
        birthday_year=1991,
    )
    _screen_user(
        phone_number="+17025550004",
        first_name="Ash",
        last_name="Smith",
        email=None,
        needs_onboarding=True,
    )
    guest = User.objects.create_user(
        phone_number="+17025550005",
        first_name="River",
        last_name="Guest",
        email="river@example.com",
        is_member=False,
        password=E2E_PASSWORD,
    )
    event = Event.objects.create(
        title="potluck",
        slug="potluck",
        description="bring a dish to share.",
        start_datetime=_POTLUCK_AT,
        location="the park",
        event_type=EventType.OFFICIAL,
        visibility=PageVisibility.PUBLIC,
        status=EventStatus.ACTIVE,
        rsvp_enabled=True,
        created_by=seed,
    )
    EventRSVP.objects.create(event=event, user=seed, status=RSVPStatus.ATTENDING)
    EventRSVP.objects.create(event=event, user=guest, status=RSVPStatus.ATTENDING)
    guest_token = NonMemberRsvpToken.issue_or_extend(guest)
    hike = Event.objects.create(
        title="hike",
        slug="hike",
        description="a short walk in the woods.",
        start_datetime=_HIKE_AT,
        location="the woods",
        event_type=EventType.OFFICIAL,
        visibility=PageVisibility.PUBLIC,
        status=EventStatus.ACTIVE,
        rsvp_enabled=True,
        created_by=seed,
    )
    Event.objects.create(
        title="picnic",
        slug="picnic",
        description="called off for rain.",
        start_datetime=_PICNIC_AT,
        location="the meadow",
        event_type=EventType.OFFICIAL,
        visibility=PageVisibility.PUBLIC,
        status=EventStatus.CANCELLED,
        rsvp_enabled=True,
        created_by=seed,
    )
    ada = _screen_user(
        phone_number="+17025550006",
        first_name="Ada",
        last_name="Admin",
        email="ada@pda.test",
        has_seen_veganniversary=True,
    )
    ada.roles.add(Role.objects.get(name="admin", is_default=True))
    _screen_user(
        phone_number="+17025550008",
        first_name="Remy",
        last_name="Reset",
        email="remy@example.com",
        needs_password_reset=True,
        has_seen_veganniversary=True,
    )
    User.objects.create_user(
        phone_number="+17025550009",
        first_name="Casey",
        last_name="Consent",
        email="casey@example.com",
        is_member=True,
        has_seen_veganniversary=True,
        guidelines_consent_at=None,
        password=E2E_PASSWORD,
    )
    FeatureFlagState.objects.update_or_create(
        key="host_attendance_report",
        defaults={"enabled": True},
    )
    survey = Survey.objects.create(
        title="potluck feedback",
        slug="potluck-feedback",
        created_by=ada,
    )
    Survey.objects.filter(pk=survey.pk).update(created_at=_RECORD_AT)
    folder = DocFolder.objects.create(name="guides")
    document = Document.objects.create(
        title="house rules",
        content_html="<p>shoes off inside.</p>",
        folder=folder,
        created_by=ada,
    )
    join_request = JoinRequest.objects.create(
        first_name="Sam",
        last_name="Applicant",
        phone_number="+17025550007",
        email="sam@example.com",
    )
    JoinRequest.objects.filter(pk=join_request.pk).update(submitted_at=_RECORD_AT)
    JoinFormQuestion.objects.create(label="how did you hear about us?")
    digest_html = render_to_string(
        "emails/weekly_digest.html",
        {
            "display_name": "Seed",
            "events": [
                {
                    "title": "potluck",
                    "when": "friday, october 9 at 6:00 pm",
                    "location": "the park",
                    "url": "http://127.0.0.1:3000/events/potluck",
                }
            ],
            "calendar_url": "http://127.0.0.1:3000/calendar",
            "settings_url": "http://127.0.0.1:3000/settings",
        },
    )
    return {
        "password": E2E_PASSWORD,
        "seed_phone": seed.phone_number,
        "seed_token": _access_token(seed),
        "jamie_id": str(jamie.id),
        "jamie_token": _access_token(jamie),
        "ash_phone": "+17025550004",
        "digest_html": digest_html,
        "event_id": str(event.id),
        "guest_token": guest_token.token,
        "hike_id": str(hike.id),
        "admin_phone": ada.phone_number,
        "reset_phone": "+17025550008",
        "consent_phone": "+17025550009",
        "survey_id": str(survey.id),
        "doc_id": str(document.id),
    }


SCENARIOS = {
    "member": _seed_member,
    "member-screens": _seed_member_screens,
    "public-new": _seed_public_new,
    "public-recognized": _seed_public_recognized,
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
        # argparse choices= already rejects any unknown scenario before handle runs.
        self.stdout.write(json.dumps(SCENARIOS[options["scenario"]]()))
