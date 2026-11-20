import secrets
from datetime import timedelta

from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from users.models import User
from users.permissions import PermissionKey

from community.models import AttendanceStatus, CancelReason, Event, EventRSVP, EventType, RSVPStatus

from ._e2e_common import browser_user, member_user, non_member_user, random_event, random_phone


def _named_member(first_name: str) -> User:
    user = member_user(random_phone())
    user.first_name = first_name
    user.save(update_fields=["first_name"])
    return user


def _attended(event: Event, user: User) -> None:
    EventRSVP.objects.create(
        event=event, user=user, status=RSVPStatus.ATTENDING, attendance=AttendanceStatus.ATTENDED
    )


def seed_report_sections(event: Event, guests: tuple[User, User, User, User, User]) -> None:
    """Fill every check-in report section with one guest, in report order, for the screenshot."""
    attended, no_show, canceled, going, maybe = guests
    _attended(event, attended)
    EventRSVP.objects.create(
        event=event, user=no_show, status=RSVPStatus.ATTENDING, attendance=AttendanceStatus.DIDNT_GO
    )
    EventRSVP.objects.create(
        event=event,
        user=canceled,
        status=RSVPStatus.CANT_GO,
        cancelled_at=event.start_datetime - timedelta(days=1),
        cancel_reason=CancelReason.SELF,
    )
    EventRSVP.objects.create(event=event, user=going, status=RSVPStatus.ATTENDING)
    EventRSVP.objects.create(event=event, user=maybe, status=RSVPStatus.MAYBE)


def seed_attendance_report() -> dict:
    # Creator with no role, so the report is reached via the host path, not MANAGE_EVENTS.
    host = browser_user()
    start = timezone.now() - timedelta(days=2)
    event = random_event(
        "attendance-report",
        start_datetime=start,
        end_datetime=start + timedelta(hours=2),
        created_by=host,
    )

    suffix = secrets.token_hex(4)
    attended = _named_member(f"Attended{suffix}")
    no_show = _named_member(f"Noshow{suffix}")
    canceled = non_member_user(random_phone())
    canceled.first_name = f"Canceled{suffix}"
    canceled.save(update_fields=["first_name"])

    _attended(event, attended)
    EventRSVP.objects.create(
        event=event, user=no_show, status=RSVPStatus.ATTENDING, attendance=AttendanceStatus.DIDNT_GO
    )
    EventRSVP.objects.create(
        event=event,
        user=canceled,
        status=RSVPStatus.CANT_GO,
        cancelled_at=timezone.now() - timedelta(days=3),
        cancel_reason=CancelReason.SELF,
    )

    return {
        "event_id": str(event.id),
        "event_title": event.title,
        "refresh_token": str(RefreshToken.for_user(host)),
        "attended_name": attended.full_name,
        "no_show_name": no_show.full_name,
        "canceled_name": canceled.full_name,
    }


def seed_attendance_analytics() -> dict:
    admin = browser_user([PermissionKey.MANAGE_EVENTS, PermissionKey.MANAGE_USERS])

    recent = [
        random_event(
            "analytics-recent",
            event_type=EventType.OFFICIAL,
            start_datetime=timezone.now() - timedelta(days=days),
        )
        for days in (10, 40)
    ]
    stale = random_event(
        "analytics-stale",
        event_type=EventType.CLUB,
        start_datetime=timezone.now() - timedelta(days=400),
    )

    # The at-risk name sorts after the compliant one, so seeing it first proves the
    # pause-candidate ranking rather than alphabetical order.
    suffix = secrets.token_hex(4)
    compliant = _named_member(f"Abby{suffix}")
    at_risk = _named_member(f"Zara{suffix}")
    for event in recent:
        _attended(event, compliant)
    _attended(stale, at_risk)

    return {
        "refresh_token": str(RefreshToken.for_user(admin)),
        "search": suffix,
        "compliant_name": compliant.full_name.lower(),
        "at_risk_name": at_risk.full_name.lower(),
    }
