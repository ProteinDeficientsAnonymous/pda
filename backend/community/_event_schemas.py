"""Pydantic schemas for event endpoints."""

import re
from datetime import datetime
from urllib.parse import urlparse

import phonenumbers
from pydantic import BaseModel, Field, field_validator, model_validator

from community._field_limits import FieldLimit
from community._validation import Code, raise_validation
from community.models import (
    AttendanceStatus,
    EventStatus,
    EventType,
    InvitePermission,
    PageVisibility,
)

# Loose RFC-5322-ish email check — Pydantic's full EmailStr validator is
# overkill for a free-text payment field, and we don't need DNS lookups.
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _looks_like_email(s: str) -> bool:
    return bool(_EMAIL_RE.match(s))


def _looks_like_phone(s: str) -> bool:
    """Accept E.164 (+15551234567) or any string phonenumbers can parse as US."""
    try:
        parsed = phonenumbers.parse(s, "US")
    except phonenumbers.phonenumberutil.NumberParseException:
        return False
    return phonenumbers.is_valid_number(parsed)


def _validate_zelle_info(v: str | None) -> str | None:
    """Zelle is a free-text field but should be either an email or a phone number."""
    if v is None or v == "":
        return v
    stripped = v.strip()
    if _looks_like_email(stripped) or _looks_like_phone(stripped):
        return stripped
    raise_validation(Code.Zelle.INVALID, field="zelle_info")


def _validate_max_attendees(v: int | None) -> int | None:
    """Accept null (unlimited) or an integer >= 1. Reject 0 and negatives."""
    if v is None:
        return v
    if v < 1:
        raise_validation(
            Code.Event.MAX_ATTENDEES_MUST_BE_AT_LEAST_ONE,
            field="max_attendees",
        )
    return v


def _require_path(url: str, field: str) -> str:
    """Validate that a URL has a non-trivial path (not bare domain)."""
    if not url:
        return url
    normalized = url if url.startswith(("http://", "https://")) else f"https://{url}"
    try:
        parsed = urlparse(normalized)
    except ValueError:
        raise_validation(Code.Url.INVALID, field=field)
    if not parsed.netloc:
        raise_validation(Code.Url.INVALID, field=field)
    path = parsed.path.rstrip("/")
    if not path:
        raise_validation(Code.Url.PATH_REQUIRED, field=field)
    return normalized


def _normalize_url(url: str) -> str:
    return url if url.startswith(("http://", "https://")) else f"https://{url}"


def _strip_www(host: str) -> str:
    return host.removeprefix("www.")


def _validate_whatsapp_url(url: str, field: str) -> str:
    known_hosts = {"chat.whatsapp.com", "wa.me", "whats.app"}
    if not url:
        return url
    try:
        parsed = urlparse(_normalize_url(url))
    except ValueError:
        raise_validation(Code.Url.INVALID, field=field)
    host = _strip_www(parsed.netloc.lower())
    if host not in known_hosts:
        raise_validation(
            Code.Url.WHATSAPP_NOT_RECOGNIZED,
            field=field,
            allowed_hosts=sorted(known_hosts),
        )
    return _require_path(url, field=field)


def _validate_partiful_url(url: str, field: str) -> str:
    if not url:
        return url
    try:
        parsed = urlparse(_normalize_url(url))
    except ValueError:
        raise_validation(Code.Url.INVALID, field=field)
    host = _strip_www(parsed.netloc.lower())
    if "partiful.com" not in host:
        raise_validation(Code.Url.PARTIFUL_NOT_RECOGNIZED, field=field)
    return _require_path(url, field=field)


def _validate_generic_url(url: str, field: str) -> str:
    # Accepts either a bare domain (fast.com) or a full URL and normalizes to
    # a full https:// URL on the way in. We don't require a path — "other_link"
    # is commonly used for landing pages and flyers.
    if not url:
        return url
    normalized = _normalize_url(url)
    try:
        parsed = urlparse(normalized)
    except ValueError:
        raise_validation(Code.Url.INVALID, field=field)
    if not parsed.netloc or "." not in parsed.netloc:
        raise_validation(Code.Url.INVALID, field=field)
    if parsed.scheme not in ("http", "https"):
        raise_validation(Code.Url.SCHEME_MUST_BE_HTTP_OR_HTTPS, field=field)
    return normalized


class RSVPGuestOut(BaseModel):
    user_id: str
    name: str
    status: str
    has_plus_one: bool = False
    phone: str | None = None
    photo_url: str = ""
    attendance: str = AttendanceStatus.UNKNOWN


class EventListOut(BaseModel):
    id: str
    title: str
    description: str
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    location: str
    latitude: float | None = None
    longitude: float | None = None
    event_type: str = EventType.COMMUNITY
    visibility: str = PageVisibility.PUBLIC
    photo_url: str = ""
    whatsapp_link: str = ""
    partiful_link: str = ""
    other_link: str = ""
    price: str = ""
    venmo_link: str = ""
    cashapp_link: str = ""
    zelle_info: str = ""
    created_by_id: str | None = None
    created_by_name: str | None = None
    created_by_photo_url: str = ""
    co_host_ids: list[str] = []
    co_host_names: list[str] = []
    co_host_photo_urls: list[str] = []
    datetime_tbd: bool = False
    has_poll: bool = False
    allow_plus_ones: bool = False
    max_attendees: int | None = None
    attending_count: int = 0
    waitlisted_count: int = 0
    invited_count: int = 0
    is_past: bool = False
    status: str = "active"


class EventOut(BaseModel):
    id: str
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
    venmo_link: str = ""
    cashapp_link: str = ""
    zelle_info: str = ""
    rsvp_enabled: bool = False
    created_by_id: str | None = None
    created_by_name: str | None = None
    created_by_photo_url: str = ""
    co_host_ids: list[str] = []
    co_host_names: list[str] = []
    co_host_photo_urls: list[str] = []
    guests: list[RSVPGuestOut] = []
    my_rsvp: str | None = None
    event_type: str = EventType.COMMUNITY
    visibility: str = PageVisibility.PUBLIC
    photo_url: str = ""
    datetime_tbd: bool = False
    allow_plus_ones: bool = False
    max_attendees: int | None = None
    attending_count: int = 0
    waitlisted_count: int = 0
    invited_count: int = 0
    survey_slugs: list[str] = []
    datetime_poll_slug: str | None = None
    has_poll: bool = False
    invited_user_ids: list[str] = []
    invited_user_names: list[str] = []
    invited_user_photo_urls: list[str] = []
    invite_permission: str = InvitePermission.ALL_MEMBERS
    is_past: bool = False
    status: str = "active"


class RSVPIn(BaseModel):
    status: str = Field(max_length=FieldLimit.CHOICE)
    has_plus_one: bool = False


class CancellationOut(BaseModel):
    user_id: str
    name: str
    cancelled_at: datetime
    days_before_event: int


class EventStatsOut(BaseModel):
    going_count: int = 0
    maybe_count: int = 0
    cant_go_count: int = 0
    no_response_count: int = 0
    waitlisted_count: int = 0
    attended_count: int = 0
    no_show_count: int = 0
    not_marked_count: int = 0
    cancellations: list[CancellationOut] = []


class AttendanceIn(BaseModel):
    attendance: str = Field(max_length=FieldLimit.CHOICE)

    @field_validator("attendance")
    @classmethod
    def validate_attendance(cls, v: str) -> str:
        valid = {AttendanceStatus.UNKNOWN, AttendanceStatus.ATTENDED, AttendanceStatus.NO_SHOW}
        if v not in valid:
            raise_validation(
                Code.Event.ATTENDANCE_INVALID_CHOICE,
                field="attendance",
                allowed=sorted(valid),
            )
        return v


class EventIn(BaseModel):
    title: str = Field(max_length=FieldLimit.TITLE)
    description: str = Field(default="", max_length=FieldLimit.DESCRIPTION)
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    location: str = Field(default="", max_length=FieldLimit.SHORT_TEXT)
    latitude: float | None = None
    longitude: float | None = None
    whatsapp_link: str = Field(default="", max_length=FieldLimit.URL)
    partiful_link: str = Field(default="", max_length=FieldLimit.URL)
    other_link: str = Field(default="", max_length=FieldLimit.URL)
    price: str = Field(default="", max_length=FieldLimit.SHORT_TEXT)
    venmo_link: str = Field(default="", max_length=FieldLimit.PAYMENT_HANDLE)
    cashapp_link: str = Field(default="", max_length=FieldLimit.PAYMENT_HANDLE)
    zelle_info: str = Field(default="", max_length=FieldLimit.SHORT_TEXT)
    rsvp_enabled: bool = False
    datetime_tbd: bool = False
    allow_plus_ones: bool = False
    max_attendees: int | None = None
    event_type: str = Field(default=EventType.COMMUNITY, max_length=FieldLimit.CHOICE)
    visibility: str = Field(default=PageVisibility.PUBLIC, max_length=FieldLimit.CHOICE)
    invite_permission: str = Field(
        default=InvitePermission.ALL_MEMBERS, max_length=FieldLimit.CHOICE
    )
    co_host_ids: list[str] = []
    invited_user_ids: list[str] = []
    status: str = Field(default=EventStatus.ACTIVE, max_length=FieldLimit.CHOICE)

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
        return _validate_whatsapp_url(v or "", field="whatsapp_link")

    @field_validator("partiful_link", mode="before")
    @classmethod
    def validate_partiful(cls, v: str) -> str:
        return _validate_partiful_url(v or "", field="partiful_link")

    @field_validator("other_link", mode="before")
    @classmethod
    def validate_other(cls, v: str) -> str:
        return _validate_generic_url(v or "", field="other_link")

    @field_validator("zelle_info", mode="after")
    @classmethod
    def validate_zelle(cls, v: str) -> str:
        return _validate_zelle_info(v) or ""

    @field_validator("max_attendees", mode="after")
    @classmethod
    def validate_max_attendees(cls, v: int | None) -> int | None:
        return _validate_max_attendees(v)


class EventPatchIn(BaseModel):
    title: str | None = Field(default=None, max_length=FieldLimit.TITLE)
    description: str | None = Field(default=None, max_length=FieldLimit.DESCRIPTION)
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    location: str | None = Field(default=None, max_length=FieldLimit.SHORT_TEXT)
    latitude: float | None = None
    longitude: float | None = None
    whatsapp_link: str | None = Field(default=None, max_length=FieldLimit.URL)
    partiful_link: str | None = Field(default=None, max_length=FieldLimit.URL)
    other_link: str | None = Field(default=None, max_length=FieldLimit.URL)
    price: str | None = Field(default=None, max_length=FieldLimit.SHORT_TEXT)
    venmo_link: str | None = Field(default=None, max_length=FieldLimit.PAYMENT_HANDLE)
    cashapp_link: str | None = Field(default=None, max_length=FieldLimit.PAYMENT_HANDLE)
    zelle_info: str | None = Field(default=None, max_length=FieldLimit.SHORT_TEXT)
    rsvp_enabled: bool | None = None
    datetime_tbd: bool | None = None
    allow_plus_ones: bool | None = None
    max_attendees: int | None = None
    event_type: str | None = Field(default=None, max_length=FieldLimit.CHOICE)
    visibility: str | None = Field(default=None, max_length=FieldLimit.CHOICE)
    invite_permission: str | None = Field(default=None, max_length=FieldLimit.CHOICE)
    co_host_ids: list[str] | None = None
    invited_user_ids: list[str] | None = None
    status: str | None = Field(default=None, max_length=FieldLimit.CHOICE)
    notify_attendees: bool | None = None

    @field_validator("whatsapp_link", mode="before")
    @classmethod
    def validate_whatsapp(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return _validate_whatsapp_url(v, field="whatsapp_link")

    @field_validator("partiful_link", mode="before")
    @classmethod
    def validate_partiful(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return _validate_partiful_url(v, field="partiful_link")

    @field_validator("other_link", mode="before")
    @classmethod
    def validate_other(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return _validate_generic_url(v, field="other_link")

    @field_validator("zelle_info", mode="after")
    @classmethod
    def validate_zelle(cls, v: str | None) -> str | None:
        return _validate_zelle_info(v)

    @field_validator("max_attendees", mode="after")
    @classmethod
    def validate_max_attendees(cls, v: int | None) -> int | None:
        return _validate_max_attendees(v)


_MAX_EVENT_PHOTO_SIZE = 10 * 1024 * 1024  # 10 MB
_ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/heic",
    "image/heif",
}
