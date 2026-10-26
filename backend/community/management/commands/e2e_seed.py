import calendar
import json
import secrets
from datetime import UTC, datetime, timedelta

from django.core.cache import caches
from django.core.management.base import BaseCommand
from django.db import connection
from django.template.loader import render_to_string
from django.utils import timezone
from notifications._email_helpers import format_eastern_datetime
from users.models import NonMemberRsvpToken, User
from users.roles import Role

from community._event_feedback_send import feedback_url
from community.models import (
    AttendanceStatus,
    DocFolder,
    Document,
    Event,
    EventFeedbackRequest,
    EventRSVP,
    EventRsvpQuestion,
    EventStatus,
    EventType,
    JoinFormQuestion,
    JoinRequest,
    PageVisibility,
    RsvpQuestionType,
    RSVPStatus,
    Survey,
    SurveyQuestion,
    SurveyQuestionType,
)

from ._e2e_attendance import _seed_attendance_analytics, _seed_attendance_report
from ._e2e_common import (
    E2E_PASSWORD,
    _access_token,
    _member_user,
    _non_member_user,
    _random_event,
    _random_phone,
)


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
_RECORD_AT = datetime(2026, 6, 1, 18, 0, tzinfo=UTC)
_WAITLIST_PHONES = ("+17025550010", "+17025550011", "+17025550012")
_WAITLIST_AT = datetime(2030, 6, 14, 22, 0, tzinfo=UTC)
_SCREEN_SLUGS = ("potluck", "hike", "picnic")
_CONSENT_AT = datetime(2020, 1, 1, tzinfo=UTC)


def _month_end(now: datetime, *, months_ago: int = 0) -> datetime:
    index = now.year * 12 + now.month - 1 - months_ago
    year, month0 = divmod(index, 12)
    last_day = calendar.monthrange(year, month0 + 1)[1]
    return datetime(year, month0 + 1, last_day, 22, 0, tzinfo=UTC)


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
    now = timezone.now()
    potluck_at = _month_end(now)
    hike_at = _month_end(now, months_ago=1)  # previous month stays past for the check-in report
    picnic_at = _month_end(now)
    Survey.objects.filter(slug="potluck-feedback").delete()
    DocFolder.objects.filter(name="guides").delete()
    JoinRequest.objects.filter(phone_number="+17025550007").delete()
    JoinFormQuestion.objects.filter(label="how did you hear about us?").delete()
    # waitlist-screens runs after the other visual specs; clear it so reruns match CI.
    Event.objects.filter(slug="supper").delete()
    User.objects.filter(phone_number__in=_SCREEN_PHONES + _WAITLIST_PHONES).delete()
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
        start_datetime=potluck_at,
        location="the park",
        event_type=EventType.OFFICIAL,
        visibility=PageVisibility.PUBLIC,
        status=EventStatus.ACTIVE,
        rsvp_enabled=True,
        created_by=seed,
    )
    EventRsvpQuestion.objects.create(
        event=event,
        label=("dietary restrictions " * 14).strip(),
        field_type=RsvpQuestionType.TEXTAREA,
        required=True,
    )
    EventRSVP.objects.create(event=event, user=seed, status=RSVPStatus.ATTENDING)
    EventRSVP.objects.create(event=event, user=guest, status=RSVPStatus.ATTENDING)
    guest_token = NonMemberRsvpToken.issue_or_extend(guest)
    hike = Event.objects.create(
        title="hike",
        slug="hike",
        description="a short walk in the woods.",
        start_datetime=hike_at,
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
        start_datetime=picnic_at,
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
                    "when": format_eastern_datetime(potluck_at).lower(),
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
        "calendar_date": potluck_at.date().isoformat(),
        "guest_token": guest_token.token,
        "hike_id": str(hike.id),
        "admin_phone": ada.phone_number,
        "reset_phone": "+17025550008",
        "consent_phone": "+17025550009",
        "survey_id": str(survey.id),
        "doc_id": str(document.id),
    }


def _seed_waitlist_screens() -> dict:
    if "django_cache" in connection.introspection.table_names():
        caches["ratelimit"].clear()
    Event.objects.filter(slug="supper").delete()
    User.objects.filter(phone_number__in=_WAITLIST_PHONES).delete()
    User.objects.filter(email__in=("hollis@pda.test", "wren@pda.test")).delete()
    host = _screen_user(
        phone_number="+17025550010",
        first_name="Hollis",
        last_name="Host",
        email="hollis@pda.test",
        has_seen_veganniversary=True,
    )
    wren = _screen_user(
        phone_number="+17025550011",
        first_name="Wren",
        last_name="Waitlist",
        email="wren@pda.test",
        has_seen_veganniversary=True,
    )
    guest = User.objects.create_user(
        phone_number="+17025550012",
        first_name="Pat",
        last_name="Guest",
        email=None,
        is_member=False,
    )
    event = Event.objects.create(
        title="supper club",
        slug="supper",
        description="six seats, one long table.",
        start_datetime=_WAITLIST_AT,
        location="the kitchen",
        event_type=EventType.OFFICIAL,
        visibility=PageVisibility.PUBLIC,
        status=EventStatus.ACTIVE,
        rsvp_enabled=True,
        allow_plus_ones=True,
        max_attendees=1,
        created_by=host,
    )
    EventRSVP.objects.create(event=event, user=host, status=RSVPStatus.ATTENDING)
    EventRSVP.objects.create(event=event, user=wren, status=RSVPStatus.WAITLISTED)
    EventRSVP.objects.create(event=event, user=guest, status=RSVPStatus.WAITLISTED)
    return {
        "password": E2E_PASSWORD,
        "wren_phone": wren.phone_number,
        "guest_token": NonMemberRsvpToken.issue_or_extend(guest).token,
    }


_FEEDBACK_QUESTION = "e2e: how was it?"


def _seed_event_feedback() -> dict:
    # club, not official: the dev seed already owns the official feedback survey slot
    start = timezone.now() - timedelta(days=1)
    event = _random_event(
        "event-feedback",
        start_datetime=start,
        end_datetime=start + timedelta(hours=2),
        event_type=EventType.CLUB,
    )
    survey, _ = Survey.objects.update_or_create(
        feedback_event_type=EventType.CLUB,
        defaults={"is_active": True, "opens_at": None, "closes_at": None, "max_responses": None},
        create_defaults={
            "title": "e2e club feedback",
            "slug": f"e2e-club-feedback-{secrets.token_hex(4)}",
            "anonymous": True,
        },
    )
    SurveyQuestion.objects.get_or_create(
        survey=survey,
        label=_FEEDBACK_QUESTION,
        defaults={"field_type": SurveyQuestionType.TEXT, "required": True},
    )
    attendee = _member_user(_random_phone())
    EventRSVP.objects.create(
        event=event,
        user=attendee,
        status=RSVPStatus.ATTENDING,
        attendance=AttendanceStatus.ATTENDED,
    )
    request = EventFeedbackRequest.objects.create(
        event=event, user=attendee, token=EventFeedbackRequest.new_token()
    )
    return {
        "event_title": event.title,
        "question_label": _FEEDBACK_QUESTION,
        "feedback_url": feedback_url(request.token),
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
    "attendance-report": _seed_attendance_report,
    "attendance-analytics": _seed_attendance_analytics,
    "waitlist-screens": _seed_waitlist_screens,
    "event-feedback": _seed_event_feedback,
}


class Command(BaseCommand):
    help = "Seed one-off data for a Playwright e2e scenario and print it as JSON."

    def add_arguments(self, parser):
        parser.add_argument("scenario", choices=sorted(SCENARIOS))

    def handle(self, *args, **options):
        # argparse choices= already rejects any unknown scenario before handle runs.
        self.stdout.write(json.dumps(SCENARIOS[options["scenario"]]()))
