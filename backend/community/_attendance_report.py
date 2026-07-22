"""Admin-only read models aggregating attendance across events and members."""

from datetime import datetime

from config.auth import gated_jwt
from django.db.models import Count, Q
from ninja import Router
from ninja.responses import Status
from pydantic import BaseModel
from users.models import User
from users.permissions import PermissionKey

from community._attendance_analytics import (
    compute_member_stats,
    is_compliant,
    member_rsvps_prefetch,
    months_since,
    user_rsvps_for_attendance,
)
from community._event_schemas import AttendanceReportOut, EventAttendanceRowOut
from community._rsvp_counts import attendance_q, going_headcount_expr, reportable_events_q
from community._shared import ErrorOut
from community._validation import Code, raise_validation
from community.models import AttendanceStatus, Event, FeatureFlag, flag_enabled

router = Router()


@router.get(
    "/events/attendance-report/",
    response={200: AttendanceReportOut, 403: ErrorOut},
    auth=gated_jwt,
)
def attendance_report(request):
    """Per-event attendance summary, newest first, for events with any mark."""
    if not request.auth.has_permission(PermissionKey.MANAGE_EVENTS):
        raise_validation(Code.Perm.DENIED, status_code=403, action="attendance_report")

    events = (
        Event.objects.filter(reportable_events_q(prefix=""))
        .annotate(
            attended_total=Count(
                "rsvps", filter=attendance_q(AttendanceStatus.ATTENDED), distinct=True
            ),
            no_show_total=Count(
                "rsvps", filter=attendance_q(AttendanceStatus.NO_SHOW), distinct=True
            ),
            going_total=going_headcount_expr(),
        )
        .filter(Q(attended_total__gt=0) | Q(no_show_total__gt=0))
        .order_by("-start_datetime")
    )

    return Status(
        200,
        AttendanceReportOut(
            events=[
                EventAttendanceRowOut(
                    event_id=str(e.id),
                    title=e.title,
                    start_datetime=e.start_datetime,
                    attended_count=e.attended_total,
                    no_show_count=e.no_show_total,
                    going_count=e.going_total,
                )
                for e in events
            ]
        ),
    )


class MemberAttendanceRowOut(BaseModel):
    """One member's attendance analytics for the admin members tab."""

    user_id: str
    full_name: str
    phone_number: str
    is_paused: bool
    last_qualifying_at: datetime | None = None
    qualifying_count_12mo: int = 0
    compliant: bool = False
    community_count: int = 0
    no_show_count: int = 0
    cancel_count: int = 0
    months_since_last_qualifying: int | None = None
    is_pause_candidate: bool = False


class MemberAttendanceAnalyticsOut(BaseModel):
    members: list[MemberAttendanceRowOut] = []


PAUSE_CANDIDATE_MONTHS = 12


def _member_attendance_row(user: User) -> MemberAttendanceRowOut:
    rsvps = user_rsvps_for_attendance(user)
    stats = compute_member_stats(rsvps)
    months = months_since(stats.last_qualifying_at)
    return MemberAttendanceRowOut(
        user_id=str(user.id),
        full_name=user.full_name,
        phone_number=user.phone_number,
        is_paused=user.is_paused,
        last_qualifying_at=stats.last_qualifying_at,
        qualifying_count_12mo=stats.qualifying_count_12mo,
        compliant=is_compliant(stats),
        community_count=stats.community_count,
        no_show_count=stats.no_show_count,
        cancel_count=stats.cancel_count,
        months_since_last_qualifying=months,
        is_pause_candidate=months is None or months >= PAUSE_CANDIDATE_MONTHS,
    )


@router.get(
    "/events/attendance-analytics/members/",
    response={200: MemberAttendanceAnalyticsOut, 403: ErrorOut},
    auth=gated_jwt,
)
def member_attendance_analytics(request):
    """Per-member qualifying-attendance analytics for the admin members tab.

    Pause candidates (no qualifying attendance in the last 12 months, or
    ever) sort first so admins triage them without scrolling.
    """
    if not request.auth.has_permission(PermissionKey.MANAGE_EVENTS):
        raise_validation(Code.Perm.DENIED, status_code=403, action="member_attendance_analytics")
    if not flag_enabled(FeatureFlag.ADMIN_ATTENDANCE_ANALYTICS):
        raise_validation(Code.Perm.DENIED, status_code=403, action="member_attendance_analytics")

    users = (
        User.objects.members()
        .filter(archived_at__isnull=True)
        .prefetch_related(member_rsvps_prefetch())
        .order_by("first_name", "last_name")
    )
    rows = [_member_attendance_row(u) for u in users]
    rows.sort(key=lambda r: not r.is_pause_candidate)
    return Status(200, MemberAttendanceAnalyticsOut(members=rows))
