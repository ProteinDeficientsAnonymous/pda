import secrets
from datetime import timedelta

from django.utils import timezone
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

from community.models import AttendanceStatus, EventRSVP, EventType, RSVPStatus

from ._e2e_common import E2E_PASSWORD, _member_user, _non_member_user, _random_event, _random_phone


def _admin_user(phone: str, permissions: list[str]) -> User:
    user = _member_user(phone)
    role = Role.objects.create(name=f"e2e-role-{secrets.token_hex(4)}", permissions=permissions)
    user.roles.add(role)
    return user


def _seed_attendance_report() -> dict:
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
        event=event, user=no_show, status=RSVPStatus.ATTENDING, attendance=AttendanceStatus.DIDNT_GO
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
