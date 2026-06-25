"""Admin-only attendance reporting across events.

Builds on the existing per-event check-in (``EventRSVP.attendance``). This is a
read-only aggregation layer: it does not record attendance — that happens in the
host check-in flow (``_event_rsvps.set_attendance``). Gated by ``MANAGE_EVENTS``,
matching the rest of the event-admin surface.
"""

from config.auth import gated_jwt
from django.db.models import Count, Q
from ninja import Router
from ninja.responses import Status
from users.permissions import PermissionKey

from community._event_schemas import AttendanceReportOut, EventAttendanceRowOut
from community._shared import ErrorOut
from community._validation import Code, raise_validation
from community.models import AttendanceStatus, Event, EventStatus, RSVPStatus

router = Router()


@router.get(
    "/events/attendance-report/",
    response={200: AttendanceReportOut, 403: ErrorOut},
    auth=gated_jwt,
)
def attendance_report(request):
    """Per-event attendance summary for every event with at least one mark.

    Only events with an attended or no-show mark are included — events nobody
    checked in for would just be noise in an attendance report. Newest first.
    """
    if not request.auth.has_permission(PermissionKey.MANAGE_EVENTS):
        raise_validation(Code.Perm.DENIED, status_code=403, action="attendance_report")

    attended_q = Q(
        rsvps__status=RSVPStatus.ATTENDING,
        rsvps__attendance=AttendanceStatus.ATTENDED,
    )
    no_show_q = Q(
        rsvps__status=RSVPStatus.ATTENDING,
        rsvps__attendance=AttendanceStatus.NO_SHOW,
    )
    going_q = Q(rsvps__status=RSVPStatus.ATTENDING)

    events = (
        Event.objects.exclude(status=EventStatus.DELETED)
        .annotate(
            attended_total=Count("rsvps", filter=attended_q, distinct=True),
            no_show_total=Count("rsvps", filter=no_show_q, distinct=True),
            going_total=Count("rsvps", filter=going_q, distinct=True),
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
