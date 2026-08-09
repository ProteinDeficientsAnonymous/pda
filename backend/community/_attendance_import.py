import logging

from config.audit import AuditTarget, AuditTargetType, audit_log
from config.auth import gated_jwt
from config.ratelimit import rate_limit
from django.utils import timezone
from ninja import File, Router
from ninja.files import UploadedFile
from ninja.responses import Status
from users.models import User
from users.permissions import PermissionKey

from community._attendance_import_matching import match_rows, parse_partiful_csv
from community._attendance_import_schemas import (
    AttendanceImportCommitIn,
    AttendanceImportCommitOut,
    AttendanceImportPreviewOut,
    EventOptionOut,
)
from community._shared import ErrorOut
from community._validation import Code, raise_validation
from community.models import (
    AttendanceStatus,
    Event,
    EventStatus,
    EventType,
    PageVisibility,
    RSVPStatus,
)

router = Router()

_MAX_CSV_SIZE = 2 * 1024 * 1024
_ALLOWED_CSV_TYPES = {"text/csv", "application/vnd.ms-excel", "text/plain"}


def _require_manage_events(request, action: str) -> None:
    if not request.auth.has_permission(PermissionKey.MANAGE_EVENTS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            persist=False,
            target=AuditTarget(type=AuditTargetType.EVENT, id="", details={"action": action}),
        )
        raise_validation(Code.Perm.DENIED, status_code=403, action=action)


@router.get(
    "/events/attendance-import/events/",
    response={200: list[EventOptionOut], 403: ErrorOut},
    auth=gated_jwt,
)
def list_attendance_import_event_options(request, q: str = ""):
    _require_manage_events(request, "list_attendance_import_event_options")
    events = Event.objects.exclude(status=EventStatus.DELETED).order_by("-start_datetime")
    if q.strip():
        events = events.filter(title__icontains=q.strip())
    return Status(
        200,
        [
            EventOptionOut(id=str(e.id), title=e.title, start_datetime=e.start_datetime)
            for e in events[:25]
        ],
    )


@router.post(
    "/events/attendance-import/preview/",
    response={200: AttendanceImportPreviewOut, 400: ErrorOut, 403: ErrorOut, 429: ErrorOut},
    auth=gated_jwt,
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="20/h")
def preview_attendance_import(
    request,
    csv_file: UploadedFile = File(...),  # ty: ignore[call-non-callable]
    event_id: str | None = None,
):
    _require_manage_events(request, "preview_attendance_import")
    if csv_file.content_type not in _ALLOWED_CSV_TYPES:
        raise_validation(Code.AttendanceImport.CSV_MALFORMED, status_code=400)
    if csv_file.size and csv_file.size > _MAX_CSV_SIZE:
        raise_validation(Code.AttendanceImport.CSV_MALFORMED, status_code=400)

    existing_rsvp_user_ids: set[str] = set()
    if event_id:
        existing_rsvp_user_ids = {
            str(uid)
            for uid in Event.objects.filter(id=event_id)
            .exclude(rsvps__user_id=None)
            .values_list("rsvps__user_id", flat=True)
        }

    rows = parse_partiful_csv(csv_file.read())
    matched, needs_review = match_rows(rows, existing_rsvp_user_ids)
    return Status(200, AttendanceImportPreviewOut(matched=matched, needs_review=needs_review))


def _require_all_rows_resolved(payload: AttendanceImportCommitIn) -> None:
    for row in payload.rows:
        if not row.user_id and not row.skip:
            raise_validation(
                Code.AttendanceImport.AMBIGUOUS_USER_PICK, status_code=400, row_index=row.row_index
            )


def _resolve_event(payload: AttendanceImportCommitIn, request) -> Event:
    if payload.event_id:
        try:
            return Event.objects.get(id=payload.event_id)
        except Event.DoesNotExist:
            raise_validation(Code.Event.NOT_FOUND, status_code=404)

    if not payload.event_title or not payload.event_date:
        raise_validation(Code.AttendanceImport.EVENT_OR_TITLE_REQUIRED, status_code=400)

    start = timezone.make_aware(
        timezone.datetime.combine(payload.event_date, timezone.datetime.min.time())
    )
    return Event.objects.create(
        title=payload.event_title,
        start_datetime=start,
        event_type=EventType.COMMUNITY,
        visibility=PageVisibility.PUBLIC,
        status=EventStatus.ACTIVE,
        rsvp_enabled=True,
        created_by=request.auth,
    )


def _resolve_status_and_attendance(row) -> tuple[str, str]:
    """Going+not-checked-in must map to attending+didnt_go — the didn't-go shape _rsvp_counts.no_show_q expects."""
    if row.checked_in:
        return RSVPStatus.ATTENDING, AttendanceStatus.ATTENDED
    if row.partiful_status.lower() == "going":
        return RSVPStatus.ATTENDING, AttendanceStatus.DIDNT_GO
    return RSVPStatus.MAYBE, AttendanceStatus.UNKNOWN


def _apply_row(event: Event, row, user: User) -> bool:
    """Upsert one EventRSVP for a resolved import row. return(bool): True if created."""
    rsvp_status, attendance = _resolve_status_and_attendance(row)
    _, created = event.rsvps.update_or_create(
        user=user,
        defaults={"status": rsvp_status, "attendance": attendance},
    )
    return created


@router.post(
    "/events/attendance-import/commit/",
    response={
        200: AttendanceImportCommitOut,
        400: ErrorOut,
        403: ErrorOut,
        404: ErrorOut,
        429: ErrorOut,
    },
    auth=gated_jwt,
)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="20/h")
def commit_attendance_import(request, payload: AttendanceImportCommitIn):
    _require_manage_events(request, "commit_attendance_import")
    _require_all_rows_resolved(payload)

    event = _resolve_event(payload, request)
    user_ids = {r.user_id for r in payload.rows if r.user_id and not r.skip}
    users_by_id = {str(u.id): u for u in User.objects.filter(id__in=user_ids)}

    created_count = updated_count = skipped_count = 0
    for row in payload.rows:
        if row.skip or not row.user_id:
            skipped_count += 1
            continue
        user = users_by_id.get(row.user_id)
        if user is None:
            skipped_count += 1
            continue
        if _apply_row(event, row, user):
            created_count += 1
        else:
            updated_count += 1

    audit_log(
        logging.INFO,
        "attendance_import_committed",
        request,
        target=AuditTarget(
            type=AuditTargetType.EVENT,
            id=str(event.id),
            details={
                "created_count": created_count,
                "updated_count": updated_count,
                "skipped_count": skipped_count,
            },
        ),
    )
    return Status(
        200,
        AttendanceImportCommitOut(
            event_id=str(event.id),
            event_title=event.title,
            created_count=created_count,
            updated_count=updated_count,
            skipped_count=skipped_count,
        ),
    )
