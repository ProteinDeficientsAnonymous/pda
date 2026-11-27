from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

from community.clubs.api import ClubOut
from community.events._field_validators import (
    check_max_attendees,
    validate_datetime_has_offset,
    validate_event_slug,
    validate_generic_url,
    validate_partiful_url,
    validate_zelle_info,
)
from community.events.price import parse_price, price_text
from community.events.rsvp_question_schemas import (
    EventRsvpQuestionIn,
    EventRsvpQuestionOut,
    RsvpAnswer,
)
from community.field_limits import FieldLimit
from community.models import (
    AttendanceStatus,
    EventStatus,
    EventType,
    InvitePermission,
    PageVisibility,
    RSVPStatus,
)
from community.models.event_slug import SLUG_MAX
from community.shared import validate_whatsapp_url
from community.validation import Code, raise_validation


class TagOut(BaseModel):
    id: str
    name: str
    slug: str


class TagIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)


class RSVPGuestOut(BaseModel):
    user_id: str
    name: str
    status: RSVPStatus
    has_plus_one: bool = False
    questionnaire_responses: dict = {}
    phone: str | None = None
    photo_url: str = Field(default="", description="Empty on event detail when unsigned.")
    attendance: AttendanceStatus = AttendanceStatus.UNKNOWN
    checked_in_at: datetime | None = None
    plus_one_attendance: AttendanceStatus = AttendanceStatus.UNKNOWN
    plus_one_checked_in_at: datetime | None = None
    is_member: bool = True
    paid_confirmed: bool = Field(
        default=False, description="Guest says they paid, or a host verified it."
    )
    payment_verified: bool = Field(default=False, description="A host verified the payment.")


class PendingCoHostInviteOut(BaseModel):
    id: str
    user_id: str
    user_name: str
    user_photo_url: str = ""
    invited_at: datetime


class EventListOut(BaseModel):
    id: str
    slug: str = ""
    title: str
    description: str
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    location: str
    event_type: str = EventType.COMMUNITY
    visibility: str = PageVisibility.PUBLIC
    price: str = ""
    price_note: str = ""
    co_host_ids: list[str] = []
    datetime_tbd: bool = False
    has_poll: bool = False
    allow_plus_ones: bool = False
    max_attendees: int | None = None
    attending_count: int = 0
    waitlisted_count: int = 0
    my_rsvp: str | None = None
    my_paid_confirmed: bool = False
    is_past: bool = False
    status: str = "active"
    is_partiful_import: bool = False
    is_legacy: bool = False
    tags: list[TagOut] = []


class EventOut(BaseModel):
    id: str
    slug: str = ""
    title: str
    description: str
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    location: str
    latitude: float | None = None
    longitude: float | None = None
    whatsapp_link: str = ""
    partiful_link: str = ""
    other_link: str = ""
    price: str = ""
    price_note: str = ""
    venmo_link: str = ""
    cashapp_link: str = ""
    zelle_info: str = ""
    accept_paypal: bool = False
    # Fee-inclusive total; "" when paypal isn't offered.
    paypal_price: str = ""
    rsvp_enabled: bool = False
    created_by_id: str | None = None
    created_by_name: str | None = None
    created_by_photo_url: str = ""
    co_host_ids: list[str] = []
    co_host_names: list[str] = []
    co_host_photo_urls: list[str] = []
    guests: list[RSVPGuestOut] = []
    my_rsvp: str | None = None
    my_questionnaire_responses: dict = {}
    my_paid_confirmed: bool = False
    viewer_user_id: str | None = None
    event_type: str = EventType.COMMUNITY
    event_format: str | None = None
    visibility: str = PageVisibility.PUBLIC
    photo_url: str = ""
    photo_updated_at: str | None = None
    datetime_tbd: bool = False
    allow_plus_ones: bool = False
    max_attendees: int | None = None
    rsvp_deadline: datetime | None = None
    rsvps_closed: bool = False
    attending_count: int = 0
    waitlisted_count: int = 0
    invited_count: int = 0
    # RSVP rows from outside the current co-hosts —
    # exactly the unpublish guard's predicate: 0 ⇔ "back to draft" is allowed.
    guest_rsvp_count: int = 0
    has_poll: bool = False
    invited_user_ids: list[str] = []
    invited_user_names: list[str] = []
    invited_user_photo_urls: list[str] = []
    invite_permission: str = InvitePermission.ALL_MEMBERS
    is_past: bool = False
    status: str = "active"
    is_partiful_import: bool = False
    is_legacy: bool = False
    pending_cohost_invites: list[PendingCoHostInviteOut] = []
    my_pending_cohost_invite_id: str | None = None
    tags: list[TagOut] = []
    club: ClubOut | None = None
    rsvp_questions: list[EventRsvpQuestionOut] = []


class RSVPIn(BaseModel):
    status: RSVPStatus
    has_plus_one: bool = False
    paid_confirmed: bool = False
    # One-shot post (EventComment / host notify); not stored on the RSVP row.
    comment: str | None = Field(default=None, max_length=FieldLimit.SHORT_TEXT)
    questionnaire_responses: dict[str, RsvpAnswer] = Field(
        default_factory=dict,
        description="Question UUID to answer; checkbox answers are a list of ticked options.",
    )


class HostRSVPIn(BaseModel):
    status: RSVPStatus
    has_plus_one: bool = False
    paid_confirmed: bool = False


class HostRSVPPaymentIn(BaseModel):
    paid_confirmed: bool


MAX_BULK_PAYMENT_VERIFY = 500


class BulkPaymentVerifyIn(BaseModel):
    user_ids: list[UUID] = Field(min_length=1, max_length=MAX_BULK_PAYMENT_VERIFY)


class BulkPaymentVerifyOut(BaseModel):
    verified_user_ids: list[str]
    already_verified_user_ids: list[str]
    event_verified_total: int = Field(description="Rsvps on the event with a verified payment now.")


class WaitlistOrderIn(BaseModel):
    user_ids: list[UUID]


class TextRecipientsOut(BaseModel):
    attending: list[str] = []
    maybe: list[str] = []
    cant_go: list[str] = []
    waitlisted: list[str] = []
    invited: list[str] = []
    co_hosts: list[str] = []


class CancellationOut(BaseModel):
    user_id: str
    name: str
    cancelled_at: datetime
    days_before_event: int
    within_24h: bool
    after_start: bool
    pre_cancel_status: RSVPStatus | None
    declined_outright: bool


class EventStatsOut(BaseModel):
    going_count: int = 0
    maybe_count: int = 0
    cant_go_count: int = 0
    no_response_count: int = 0
    waitlisted_count: int = 0
    attended_count: int = 0
    didnt_go_count: int = 0
    not_marked_count: int = 0
    cancellations: list[CancellationOut] = []


class EventAttendanceRowOut(BaseModel):
    """One event's attendance summary for the admin attendance report."""

    event_id: str
    title: str
    event_type: str
    start_datetime: datetime | None = None
    attended_count: int = 0
    no_show_count: int = 0
    going_count: int = 0


class AttendanceReportOut(BaseModel):
    events: list[EventAttendanceRowOut] = []
    official_no_show_count: int = 0
    club_no_show_count: int = 0


class AttendanceIn(BaseModel):
    attendance: AttendanceStatus
    for_plus_one: bool = False


class EventIn(BaseModel):
    title: str = Field(max_length=FieldLimit.TITLE)
    description: str = Field(default="", max_length=FieldLimit.EVENT_DESCRIPTION)
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    location: str = Field(default="", max_length=FieldLimit.SHORT_TEXT)
    latitude: float | None = None
    longitude: float | None = None
    whatsapp_link: str = Field(default="", max_length=FieldLimit.URL)
    partiful_link: str = Field(default="", max_length=FieldLimit.URL)
    other_link: str = Field(default="", max_length=FieldLimit.URL)
    price: str = Field(default="", max_length=FieldLimit.SHORT_TEXT)
    price_note: str = Field(default="", max_length=FieldLimit.PRICE_NOTE)
    venmo_link: str = Field(default="", max_length=FieldLimit.PAYMENT_HANDLE)
    cashapp_link: str = Field(default="", max_length=FieldLimit.PAYMENT_HANDLE)
    zelle_info: str = Field(default="", max_length=FieldLimit.SHORT_TEXT)
    accept_paypal: bool = False
    rsvp_enabled: bool = False
    datetime_tbd: bool = False
    allow_plus_ones: bool = False
    max_attendees: int | None = None
    rsvp_deadline: datetime | None = None
    event_type: str = Field(default=EventType.COMMUNITY, max_length=FieldLimit.CHOICE)
    event_format: str | None = Field(default=None, max_length=FieldLimit.CHOICE)
    visibility: str = Field(default=PageVisibility.PUBLIC, max_length=FieldLimit.CHOICE)
    invite_permission: str = Field(
        default=InvitePermission.ALL_MEMBERS, max_length=FieldLimit.CHOICE
    )
    co_host_ids: list[str] = []
    tag_ids: list[str] = []
    club_id: UUID | None = None
    rsvp_questions: list[EventRsvpQuestionIn] = []
    status: str = Field(default=EventStatus.ACTIVE, max_length=FieldLimit.CHOICE)
    is_legacy: bool = False
    is_partiful_import: bool = False

    @property
    def is_imported(self) -> bool:
        return self.is_legacy or self.is_partiful_import

    @model_validator(mode="after")
    def require_start_datetime_unless_tbd(self) -> "EventIn":
        # Drafts are intentionally saveable with incomplete info; the
        # "needs a date" rule only applies when publishing.
        if self.status == EventStatus.DRAFT:
            return self
        if not self.datetime_tbd and self.start_datetime is None:
            raise_validation(
                Code.Event.START_DATETIME_REQUIRED_UNLESS_TBD,
                field="start_datetime",
            )
        return self

    @field_validator("whatsapp_link", mode="before")
    @classmethod
    def validate_whatsapp(cls, v: str) -> str:
        return validate_whatsapp_url(v or "", field="whatsapp_link")

    @field_validator("partiful_link", mode="before")
    @classmethod
    def validate_partiful(cls, v: str) -> str:
        return validate_partiful_url(v or "", field="partiful_link")

    @field_validator("other_link", mode="before")
    @classmethod
    def validate_other(cls, v: str) -> str:
        return validate_generic_url(v or "", field="other_link")

    @field_validator("price", mode="before")
    @classmethod
    def validate_price(cls, v: object) -> str:
        return price_text(parse_price(v))

    @field_validator("zelle_info", mode="after")
    @classmethod
    def validate_zelle(cls, v: str) -> str:
        return validate_zelle_info(v) or ""

    @field_validator("max_attendees", mode="after")
    @classmethod
    def validate_max_attendees(cls, v: int | None) -> int | None:
        return check_max_attendees(v)

    @field_validator("start_datetime", "end_datetime", "rsvp_deadline", mode="after")
    @classmethod
    def validate_datetime_offset(cls, v: datetime | None, info: ValidationInfo) -> datetime | None:
        return validate_datetime_has_offset(v, info)


class EventPatchIn(BaseModel):
    title: str | None = Field(default=None, max_length=FieldLimit.TITLE)
    slug: str | None = Field(default=None, max_length=SLUG_MAX)
    description: str | None = Field(default=None, max_length=FieldLimit.EVENT_DESCRIPTION)
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    location: str | None = Field(default=None, max_length=FieldLimit.SHORT_TEXT)
    latitude: float | None = None
    longitude: float | None = None
    whatsapp_link: str | None = Field(default=None, max_length=FieldLimit.URL)
    partiful_link: str | None = Field(default=None, max_length=FieldLimit.URL)
    other_link: str | None = Field(default=None, max_length=FieldLimit.URL)
    price: str | None = Field(default=None, max_length=FieldLimit.SHORT_TEXT)
    price_note: str | None = Field(default=None, max_length=FieldLimit.PRICE_NOTE)
    venmo_link: str | None = Field(default=None, max_length=FieldLimit.PAYMENT_HANDLE)
    cashapp_link: str | None = Field(default=None, max_length=FieldLimit.PAYMENT_HANDLE)
    zelle_info: str | None = Field(default=None, max_length=FieldLimit.SHORT_TEXT)
    accept_paypal: bool | None = None
    rsvp_enabled: bool | None = None
    datetime_tbd: bool | None = None
    allow_plus_ones: bool | None = None
    max_attendees: int | None = None
    rsvp_deadline: datetime | None = None
    rsvps_closed: bool | None = None
    event_type: str | None = Field(default=None, max_length=FieldLimit.CHOICE)
    event_format: str | None = Field(default=None, max_length=FieldLimit.CHOICE)
    visibility: str | None = Field(default=None, max_length=FieldLimit.CHOICE)
    invite_permission: str | None = Field(default=None, max_length=FieldLimit.CHOICE)
    co_host_ids: list[str] | None = None
    tag_ids: list[str] | None = None
    club_id: UUID | None = None
    status: str | None = Field(default=None, max_length=FieldLimit.CHOICE)
    notify_attendees: bool | None = None
    force: bool | None = None

    @field_validator("slug", mode="after")
    @classmethod
    def validate_slug(cls, v: str | None) -> str | None:
        return None if v is None else validate_event_slug(v)

    @field_validator("whatsapp_link", mode="before")
    @classmethod
    def validate_whatsapp(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return validate_whatsapp_url(v, field="whatsapp_link")

    @field_validator("partiful_link", mode="before")
    @classmethod
    def validate_partiful(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return validate_partiful_url(v, field="partiful_link")

    @field_validator("other_link", mode="before")
    @classmethod
    def validate_other(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return validate_generic_url(v, field="other_link")

    @field_validator("price", mode="before")
    @classmethod
    def validate_price(cls, v: object) -> str | None:
        # Blank clears the price (stored as null).
        return None if v is None else price_text(parse_price(v)) or None

    @field_validator("zelle_info", mode="after")
    @classmethod
    def validate_zelle(cls, v: str | None) -> str | None:
        return validate_zelle_info(v)

    @field_validator("max_attendees", mode="after")
    @classmethod
    def validate_max_attendees(cls, v: int | None) -> int | None:
        return check_max_attendees(v)

    @field_validator("start_datetime", "end_datetime", "rsvp_deadline", mode="after")
    @classmethod
    def validate_datetime_offset(cls, v: datetime | None, info: ValidationInfo) -> datetime | None:
        return validate_datetime_has_offset(v, info)


MAX_EVENT_PHOTO_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EVENT_PHOTO_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/heic",
    "image/heif",
}
