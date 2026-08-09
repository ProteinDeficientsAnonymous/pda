import csv
import io

from users.models import User

from community._attendance_import_schemas import ImportCandidateOut, ImportRowOut
from community._validation import Code, raise_validation

REQUIRED_COLUMNS = {"name", "status", "checked in"}


def parse_partiful_csv(raw: bytes) -> list[dict[str, str]]:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise_validation(Code.AttendanceImport.CSV_MALFORMED, status_code=400)

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise_validation(Code.AttendanceImport.CSV_EMPTY, status_code=400)

    headers = {(h or "").strip().lower() for h in reader.fieldnames}
    if not REQUIRED_COLUMNS.issubset(headers):
        raise_validation(Code.AttendanceImport.CSV_MALFORMED, status_code=400)

    rows = [
        {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()} for row in reader
    ]
    if not rows:
        raise_validation(Code.AttendanceImport.CSV_EMPTY, status_code=400)
    return rows


def _candidate_pool() -> list[User]:
    return list(User.objects.active_members().filter(needs_onboarding=False))


def _matches_name(user: User, name_lower: str) -> bool:
    candidates = {user.full_name, user.nickname, f"{user.first_name} {user.nickname}".strip()}
    return name_lower in {c.strip().lower() for c in candidates if c}


def match_row(
    row_index: int, raw_row: dict[str, str], pool: list[User], existing_rsvp_user_ids: set[str]
) -> ImportRowOut:
    raw_name = raw_row.get("name", "")
    name_lower = raw_name.strip().lower()
    checked_in = raw_row.get("checked in", "").strip().lower() == "yes"
    partiful_status = raw_row.get("status", "")

    matches = [u for u in pool if name_lower and _matches_name(u, name_lower)]

    if len(matches) == 1:
        user = matches[0]
        return ImportRowOut(
            row_index=row_index,
            raw_name=raw_name,
            partiful_status=partiful_status,
            checked_in=checked_in,
            matched_user_id=str(user.id),
            matched_full_name=user.full_name,
            has_existing_rsvp=str(user.id) in existing_rsvp_user_ids,
        )

    return ImportRowOut(
        row_index=row_index,
        raw_name=raw_name,
        partiful_status=partiful_status,
        checked_in=checked_in,
        candidates=[
            ImportCandidateOut(
                user_id=str(u.id), full_name=u.full_name, phone_number=u.phone_number
            )
            for u in matches
        ],
    )


def match_rows(
    rows: list[dict[str, str]], existing_rsvp_user_ids: set[str] | None = None
) -> tuple[list[ImportRowOut], list[ImportRowOut]]:
    pool = _candidate_pool()
    existing = existing_rsvp_user_ids or set()
    matched, needs_review = [], []
    for i, row in enumerate(rows):
        result = match_row(i, row, pool, existing)
        (matched if result.matched_user_id else needs_review).append(result)
    return matched, needs_review
