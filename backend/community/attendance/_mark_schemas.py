from datetime import date

from pydantic import BaseModel


class AttendanceMarkIn(BaseModel):
    event_id: str | None = None
    event_title: str | None = None
    event_date: date | None = None
    event_type: str | None = None
    user_ids: list[str] = []


class AttendanceMarkOut(BaseModel):
    event_id: str
    event_title: str
    created_count: int
    updated_count: int
    skipped_count: int
