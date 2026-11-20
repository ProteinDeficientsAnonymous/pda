from datetime import datetime

from pydantic import BaseModel


class ReportPlusOne:
    GUEST = "guest"
    YES = "yes"
    NO = "no"


class ReportBucket:
    """Keys matching CheckInReportOut's list fields, for building the bucket dict in one place."""

    ATTENDED = "attended"
    NO_SHOWS = "no_shows"
    CANCELED = "canceled"
    UNMARKED_GOING = "unmarked_going"
    UNMARKED_NOT_GOING = "unmarked_not_going"


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
    canceled_count: int = 0
    unmarked_going_count: int = 0
    unmarked_not_going_count: int = 0
    attended: list[AttendedPersonOut] = []
    no_shows: list[CheckInReportPersonOut] = []
    canceled: list[CanceledPersonOut] = []
    unmarked_going: list[CheckInReportPersonOut] = []
    unmarked_not_going: list[CheckInReportPersonOut] = []


REPORT_CSV_COLUMNS = (
    "name",
    "phone",
    "rsvp_status",
    "attendance",
    "cancelled_at",
    "plus_one",
)
