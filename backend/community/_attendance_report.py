"""Admin-only read model aggregating per-event check-in across events."""

from config.auth import gated_jwt
from django.db.models import Count, Q
from ninja import Router
from ninja.responses import Status
from users.permissions import PermissionKey

from community._event_schemas import AttendanceReportOut, EventAttendanceRowOut
from community._rsvp_counts import attendance_q, going_headcount_expr, reportable_events_q
from community._shared import ErrorOut
from community._validation import Code, raise_validation
from community.models import AttendanceStatus, Event

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
