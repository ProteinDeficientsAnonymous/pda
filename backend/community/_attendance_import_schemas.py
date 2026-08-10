from datetime import date, datetime

from pydantic import BaseModel


class ImportCandidateOut(BaseModel):
    user_id: str
    full_name: str
    phone_number: str


class ImportRowOut(BaseModel):
    row_index: int
    raw_name: str
    partiful_status: str
    checked_in: bool
    matched_user_id: str | None = None
    matched_full_name: str | None = None
    candidates: list[ImportCandidateOut] = []
    has_existing_rsvp: bool = False


class AttendanceImportPreviewOut(BaseModel):
    matched: list[ImportRowOut] = []
    needs_review: list[ImportRowOut] = []


class ImportRowResolutionIn(BaseModel):
    row_index: int
    raw_name: str
    partiful_status: str
    checked_in: bool
    user_id: str | None = None
    skip: bool = False


class AttendanceImportCommitIn(BaseModel):
    event_id: str | None = None
    event_title: str | None = None
    event_date: date | None = None
    event_type: str | None = None
    rows: list[ImportRowResolutionIn]


class AttendanceImportCommitOut(BaseModel):
    event_id: str
    event_title: str
    created_count: int
    updated_count: int
    skipped_count: int


class EventOptionOut(BaseModel):
    id: str
    title: str
    start_datetime: datetime | None = None
