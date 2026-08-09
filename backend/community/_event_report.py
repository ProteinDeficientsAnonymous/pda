import csv
import io
from uuid import UUID

from config.auth import gated_jwt
from django.http import HttpResponse
from ninja import Router
from ninja.responses import Status
from users._helpers import visible_display_name

from community._event_helpers import is_cohost, load_event_with_stats_prefetch
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


def _report_rsvps(event: Event):
    # REMOVED RSVPs are soft-deleted off the guest list; every other status is
    # a real attendee the report must account for.
    return [r for r in event.rsvps.all() if r.status != RSVPStatus.REMOVED]


def _person(
    rsvp, viewer, can_see_phones: bool, is_plus_one_guest: bool = False
) -> CheckInReportPersonOut:
    return CheckInReportPersonOut(
        user_id=str(rsvp.user_id),
        name=visible_display_name(rsvp.user, viewer),
        phone=rsvp.user.phone_number if can_see_phones else None,
        is_member=rsvp.user.is_member,
        is_plus_one_guest=is_plus_one_guest,
    )


def _classify_person(rsvp, person: CheckInReportPersonOut, buckets: dict) -> None:
    if rsvp.status == RSVPStatus.CANT_GO:
        buckets["canceled"].append(
            CanceledPersonOut(
                **person.model_dump(), cancelled_at=rsvp.cancelled_at or rsvp.updated_at
            )
        )
    elif rsvp.status == RSVPStatus.ATTENDING and rsvp.attendance == AttendanceStatus.ATTENDED:
        buckets["attended"].append(
            AttendedPersonOut(**person.model_dump(), checked_in_at=rsvp.checked_in_at)
        )
    elif rsvp.status == RSVPStatus.ATTENDING and rsvp.attendance == AttendanceStatus.NO_SHOW:
        buckets["no_shows"].append(person)
    else:
        buckets["unmarked"].append(person)


def _classify_plus_one(rsvp, person: CheckInReportPersonOut, buckets: dict) -> None:
    if rsvp.status == RSVPStatus.ATTENDING and rsvp.attendance == AttendanceStatus.ATTENDED:
        buckets["attended"].append(
            AttendedPersonOut(**person.model_dump(), checked_in_at=rsvp.checked_in_at)
        )
    else:
        buckets["unmarked"].append(person)


def _build_report(event: Event, viewer) -> CheckInReportOut:
    co_host_ids = {str(c.id) for c in event.co_hosts.all()}
    can_see_phones = is_cohost(viewer, co_host_ids)

    buckets = {"attended": [], "no_shows": [], "canceled": [], "unmarked": []}
    for rsvp in _report_rsvps(event):
        _classify_person(rsvp, _person(rsvp, viewer, can_see_phones), buckets)
        if rsvp.has_plus_one:
            plus_one = _person(rsvp, viewer, can_see_phones, is_plus_one_guest=True)
            _classify_plus_one(rsvp, plus_one, buckets)

    return CheckInReportOut(
        attended_count=len(buckets["attended"]),
        no_show_count=len(buckets["no_shows"]),
        canceled_count=len(buckets["canceled"]),
        unmarked_count=len(buckets["unmarked"]),
        attended=buckets["attended"],
        no_shows=buckets["no_shows"],
        canceled=buckets["canceled"],
        unmarked=buckets["unmarked"],
    )


@router.get(
    "/events/{event_id}/report/",
    response={200: CheckInReportOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def get_check_in_report(request, event_id: UUID):
    event = _load_and_authorize(request, event_id)
    return Status(200, _build_report(event, request.auth))


def _csv_safe(value: str) -> str:
    # Prefix a leading apostrophe so spreadsheet apps don't execute
    # attendee-controlled names/phones as formulas (CSV injection).
    if value and value[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


def _csv_row(
    rsvp, viewer, can_see_phones: bool, columns: list[str], is_plus_one_guest: bool = False
) -> list[str]:
    values = {
        "name": _csv_safe(visible_display_name(rsvp.user, viewer)),
        "phone": _csv_safe((rsvp.user.phone_number or "") if can_see_phones else ""),
        "rsvp_status": rsvp.status,
        "attendance": rsvp.attendance,
        "checked_in_at": rsvp.checked_in_at.isoformat() if rsvp.checked_in_at else "",
        "cancelled_at": rsvp.cancelled_at.isoformat() if rsvp.cancelled_at else "",
        "plus_one": "guest" if is_plus_one_guest else ("yes" if rsvp.has_plus_one else "no"),
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

    co_host_ids = {str(c.id) for c in event.co_hosts.all()}
    can_see_phones = is_cohost(request.auth, co_host_ids)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(selected)
    for rsvp in _report_rsvps(event):
        writer.writerow(_csv_row(rsvp, request.auth, can_see_phones, selected))
        if rsvp.has_plus_one:
            writer.writerow(
                _csv_row(rsvp, request.auth, can_see_phones, selected, is_plus_one_guest=True)
            )

    response = HttpResponse(buf.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{_report_csv_filename(event)}"'
    return response
