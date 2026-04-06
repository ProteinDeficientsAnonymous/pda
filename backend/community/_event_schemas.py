"""Pydantic schemas for event endpoints."""

from datetime import datetime

from pydantic import BaseModel

from community.models import EventType, InvitePermission, PageVisibility


class RSVPGuestOut(BaseModel):
    user_id: str
    name: str
    status: str
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
    co_host_ids: list[str] = []
    co_host_names: list[str] = []
    co_host_photo_urls: list[str] = []
    guests: list[RSVPGuestOut] = []
    my_rsvp: str | None = None
    event_type: str = EventType.COMMUNITY
    visibility: str = PageVisibility.PUBLIC
    photo_url: str = ""
    datetime_tbd: bool = False
    survey_slugs: list[str] = []
    datetime_poll_slug: str | None = None
    has_poll: bool = False
    invited_user_ids: list[str] = []
    invited_user_names: list[str] = []
    invited_user_photo_urls: list[str] = []
    invite_permission: str = InvitePermission.ALL_MEMBERS


class RSVPIn(BaseModel):
    status: str


class EventIn(BaseModel):
    title: str
    description: str = ""
    start_datetime: datetime
    end_datetime: datetime | None = None
    location: str = ""
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
    datetime_tbd: bool = False
    event_type: str = EventType.COMMUNITY
    visibility: str = PageVisibility.PUBLIC
    invite_permission: str = InvitePermission.ALL_MEMBERS
    co_host_ids: list[str] = []
    invited_user_ids: list[str] = []


class EventPatchIn(BaseModel):
    title: str | None = None
    description: str | None = None
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    location: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    whatsapp_link: str | None = None
    partiful_link: str | None = None
    other_link: str | None = None
    price: str | None = None
    venmo_link: str | None = None
    cashapp_link: str | None = None
    zelle_info: str | None = None
    rsvp_enabled: bool | None = None
    datetime_tbd: bool | None = None
    event_type: str | None = None
    visibility: str | None = None
    invite_permission: str | None = None
    co_host_ids: list[str] | None = None
    invited_user_ids: list[str] | None = None


_MAX_EVENT_PHOTO_SIZE = 10 * 1024 * 1024  # 10 MB
_ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/heic",
    "image/heif",
}
