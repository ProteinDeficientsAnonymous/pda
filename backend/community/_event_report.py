import csv
import io
from uuid import UUID

from config.auth import gated_jwt
from django.http import HttpResponse
from ninja import Router
from ninja.responses import Status
from users._helpers import visible_display_name

from community._event_helpers import _can_see_phones, load_event_with_stats_prefetch
from community._event_report_schemas import (
    REPORT_CSV_COLUMNS,
    AttendedPersonOut,
    CanceledPersonOut,
    CheckInReportOut,
    CheckInReportPersonOut,
)
from community._events import _can_edit_event
from community._shared import ErrorOut
from community._validation import Code, raise_validation
from community.models import AttendanceStatus, Event, FeatureFlag, RSVPStatus, flag_enabled

router = Router()


def _load_and_authorize(request, event_id: UUID) -> Event:
    event = load_event_with_stats_prefetch(event_id)
    if event is None:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    if not _can_edit_event(request.auth, event):
        raise_validation(Code.Perm.DENIED, status_code=403, action="check_in_report")
    if not flag_enabled(FeatureFlag.HOST_ATTENDANCE_REPORT):
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    if not event.is_past:
        raise_validation(Code.Event.CHECK_IN_REPORT_NOT_YET_AVAILABLE, status_code=400)
    return event


def _person(rsvp, can_see_phones: bool) -> CheckInReportPersonOut:
    return CheckInReportPersonOut(
        user_id=str(rsvp.user_id),
        name=visible_display_name(rsvp.user, None),
        phone=rsvp.user.phone_number if can_see_phones else None,
        is_member=rsvp.user.is_member,
    )


def _build_report(event: Event, viewer) -> CheckInReportOut:
    creator = event.created_by
    co_host_ids = {str(c.id) for c in event.co_hosts.all()}
    can_see_phones = _can_see_phones(viewer, creator, co_host_ids)

    attended, no_shows, canceled, unmarked = [], [], [], []
    for rsvp in event.rsvps.all():
        base = _person(rsvp, can_see_phones)
        if rsvp.status == RSVPStatus.CANT_GO:
            canceled.append(
                CanceledPersonOut(
                    **base.model_dump(), cancelled_at=rsvp.cancelled_at or rsvp.updated_at
                )
            )
        elif rsvp.status == RSVPStatus.ATTENDING and rsvp.attendance == AttendanceStatus.ATTENDED:
            attended.append(
                AttendedPersonOut(**base.model_dump(), checked_in_at=rsvp.checked_in_at)
            )
        elif rsvp.status == RSVPStatus.ATTENDING and rsvp.attendance == AttendanceStatus.NO_SHOW:
            no_shows.append(base)
        elif rsvp.status == RSVPStatus.ATTENDING:
            unmarked.append(base)

    return CheckInReportOut(
        attended_count=len(attended),
        no_show_count=len(no_shows),
        canceled_count=len(canceled),
        unmarked_count=len(unmarked),
        attended=attended,
        no_shows=no_shows,
        canceled=canceled,
        unmarked=unmarked,
    )


@router.get(
    "/events/{event_id}/report/",
    response={200: CheckInReportOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def get_check_in_report(request, event_id: UUID):
    event = _load_and_authorize(request, event_id)
    return Status(200, _build_report(event, request.auth))


def _csv_row(rsvp, can_see_phones: bool, columns: list[str]) -> list[str]:
    values = {
        "name": visible_display_name(rsvp.user, None),
        "phone": (rsvp.user.phone_number or "") if can_see_phones else "",
        "rsvp_status": rsvp.status,
        "attendance": rsvp.attendance,
        "checked_in_at": rsvp.checked_in_at.isoformat() if rsvp.checked_in_at else "",
        "cancelled_at": rsvp.cancelled_at.isoformat() if rsvp.cancelled_at else "",
        "plus_one": "yes" if rsvp.has_plus_one else "no",
    }
    return [values[c] for c in columns]


def _parse_columns(raw: str) -> list[str]:
    columns = [c.strip() for c in raw.split(",") if c.strip()]
    for column in columns:
        if column not in REPORT_CSV_COLUMNS:
            raise_validation(
                Code.Event.CHECK_IN_REPORT_INVALID_COLUMN, status_code=422, column=column
            )
    return columns


def _report_csv_filename(event: Event) -> str:
    return f"check-in-report-{event.id}.csv"


@router.get(
    "/events/{event_id}/report.csv",
    response={400: ErrorOut, 403: ErrorOut, 404: ErrorOut, 422: ErrorOut},
    auth=gated_jwt,
)
def get_check_in_report_csv(request, event_id: UUID, columns: str = ",".join(REPORT_CSV_COLUMNS)):
    event = _load_and_authorize(request, event_id)
    selected = _parse_columns(columns)

    creator = event.created_by
    co_host_ids = {str(c.id) for c in event.co_hosts.all()}
    can_see_phones = _can_see_phones(request.auth, creator, co_host_ids)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(selected)
    for rsvp in event.rsvps.all():
        writer.writerow(_csv_row(rsvp, can_see_phones, selected))

    response = HttpResponse(buf.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{_report_csv_filename(event)}"'
    return response
