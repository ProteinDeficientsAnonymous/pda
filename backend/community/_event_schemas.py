"""Pydantic schemas for event endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field

from community._field_limits import FieldLimit
from community.models import EventType, InvitePermission, PageVisibility


class RSVPGuestOut(BaseModel):
    user_id: str
    name: str
    status: str
    has_plus_one: bool = False
    phone: str | None = None
    photo_url: str = ""


class EventListOut(BaseModel):
    id: str
    title: str
    description: str
    start_datetime: datetime
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
    co_host_ids: list[str] = []
    co_host_names: list[str] = []
    datetime_tbd: bool = False
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
    start_datetime: datetime
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


class EventIn(BaseModel):
    title: str = Field(max_length=FieldLimit.TITLE)
    description: str = Field(default="", max_length=FieldLimit.DESCRIPTION)
    start_datetime: datetime
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


_MAX_EVENT_PHOTO_SIZE = 10 * 1024 * 1024  # 10 MB
_ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/heic",
    "image/heif",
}
