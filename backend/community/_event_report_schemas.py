from datetime import datetime

from pydantic import BaseModel


class ReportPlusOne:
    GUEST = "guest"
    YES = "yes"
    NO = "no"


class CheckInReportPersonOut(BaseModel):
    user_id: str
    name: str
    phone: str | None = None
    is_member: bool = True
    is_plus_one_guest: bool = False


class AttendedPersonOut(CheckInReportPersonOut):
    checked_in_at: datetime | None = None


class CanceledPersonOut(CheckInReportPersonOut):
    cancelled_at: datetime


class CheckInReportOut(BaseModel):
    attended_count: int = 0
    no_show_count: int = 0
    didnt_go_count: int = 0
    canceled_count: int = 0
    unmarked_count: int = 0
    attended: list[AttendedPersonOut] = []
    no_shows: list[CheckInReportPersonOut] = []
    didnt_go: list[CheckInReportPersonOut] = []
    canceled: list[CanceledPersonOut] = []
    unmarked: list[CheckInReportPersonOut] = []


REPORT_CSV_COLUMNS = (
    "name",
    "phone",
    "rsvp_status",
    "attendance",
    "cancelled_at",
    "plus_one",
)
