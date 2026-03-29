import logging
import re
from datetime import datetime
from uuid import UUID

import phonenumbers
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.mail import send_mail
from django.http import HttpRequest
from ninja import Router
from ninja.responses import Status
from ninja.security import HttpBearer
from ninja_jwt.authentication import JWTAuth, JWTBaseAuthentication
from pydantic import BaseModel, Field
from users.models import User as UserModel
from users.permissions import PermissionKey

from community.models import (
    CommunityGuidelines,
    EditablePage,
    Event,
    EventRSVP,
    HomePage,
    JoinRequest,
    JoinRequestStatus,
    PageVisibility,
    RSVPStatus,
    WhatsAppConfig,
)

logger = logging.getLogger("pda.community")

router = Router()


class OptionalJWTAuth(JWTBaseAuthentication, HttpBearer):
    """JWT auth that returns AnonymousUser instead of None/401 when no/invalid token."""

    def authenticate(self, request: HttpRequest, token: str):
        try:
            return self.jwt_authenticate(request, token)
        except Exception:
            return AnonymousUser()

    def __call__(self, request: HttpRequest):
        result = super().__call__(request)
        # No Authorization header → super().__call__ returns None
        if result is None:
            return AnonymousUser()
        return result


_optional_jwt = OptionalJWTAuth()


class GuidelinesOut(BaseModel):
    content: str
    updated_at: datetime


class GuidelinesPatchIn(BaseModel):
    content: str


class JoinRequestIn(BaseModel):
    display_name: str
    phone_number: str
    email: str = ""
    pronouns: str = ""
    how_they_heard: str = ""
    why_join: str


class JoinRequestOut(BaseModel):
    id: str
    display_name: str
    phone_number: str
    email: str
    pronouns: str
    how_they_heard: str
    why_join: str
    submitted_at: datetime
    status: str


class JoinRequestStatusIn(BaseModel):
    status: str


class ApproveJoinRequestOut(BaseModel):
    id: str
    display_name: str
    phone_number: str
    status: str
    temporary_password: str | None = None


class RSVPGuestOut(BaseModel):
    user_id: str
    name: str
    status: str
    phone: str | None = None


class EventOut(BaseModel):
    id: str
    title: str
    description: str
    start_datetime: datetime
    end_datetime: datetime | None = None
    location: str
    whatsapp_link: str = ""
    partiful_link: str = ""
    other_link: str = ""
    rsvp_enabled: bool = False
    created_by_id: str | None = None
    created_by_name: str | None = None
    co_host_ids: list[str] = []
    co_host_names: list[str] = []
    guests: list[RSVPGuestOut] = []
    my_rsvp: str | None = None


class RSVPIn(BaseModel):
    status: str


class ErrorReportIn(BaseModel):
    error: str = Field(max_length=2000)
    stack_trace: str = Field(default="", max_length=10000)
    context: str = Field(default="", max_length=500)


class ErrorReportOut(BaseModel):
    detail: str


class ErrorOut(BaseModel):
    detail: str


class EditablePageOut(BaseModel):
    slug: str
    content: str
    visibility: str
    updated_at: datetime


class EditablePagePatchIn(BaseModel):
    content: str | None = None
    visibility: str | None = None


class EventIn(BaseModel):
    title: str
    description: str = ""
    start_datetime: datetime
    end_datetime: datetime | None = None
    location: str = ""
    whatsapp_link: str = ""
    partiful_link: str = ""
    other_link: str = ""
    rsvp_enabled: bool = False
    co_host_ids: list[str] = []


class EventPatchIn(BaseModel):
    title: str | None = None
    description: str | None = None
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    location: str | None = None
    whatsapp_link: str | None = None
    partiful_link: str | None = None
    other_link: str | None = None
    rsvp_enabled: bool | None = None
    co_host_ids: list[str] | None = None


DISPLAY_NAME_RE = re.compile(r"^[a-zA-Z ]+$")


def _validate_phone(raw: str) -> str:
    try:
        parsed = phonenumbers.parse(raw, None)
    except phonenumbers.phonenumberutil.NumberParseException as e:
        raise ValueError(str(e)) from e
    if not phonenumbers.is_valid_number(parsed):
        raise ValueError(f"Invalid phone number: {raw}")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


@router.get("/guidelines/", response={200: GuidelinesOut}, auth=JWTAuth())
def get_guidelines(request):
    g = CommunityGuidelines.get()
    return Status(200, GuidelinesOut(content=g.content, updated_at=g.updated_at))


@router.patch("/guidelines/", response={200: GuidelinesOut, 403: ErrorOut}, auth=JWTAuth())
def update_guidelines(request, payload: GuidelinesPatchIn):
    if not request.auth.has_permission(PermissionKey.MANAGE_GUIDELINES):
        return Status(403, ErrorOut(detail="Permission denied."))
    g = CommunityGuidelines.get()
    g.content = payload.content
    g.save()
    return Status(200, GuidelinesOut(content=g.content, updated_at=g.updated_at))


class HomePageOut(BaseModel):
    content: str
    join_content: str
    donate_url: str
    updated_at: datetime


class HomePagePatchIn(BaseModel):
    content: str | None = None
    join_content: str | None = None
    donate_url: str | None = None


@router.get("/home/", response={200: HomePageOut}, auth=None)
def get_home(request):
    h = HomePage.get()
    return Status(
        200,
        HomePageOut(
            content=h.content,
            join_content=h.join_content,
            donate_url=h.donate_url,
            updated_at=h.updated_at,
        ),
    )


@router.patch("/home/", response={200: HomePageOut, 403: ErrorOut}, auth=JWTAuth())
def update_home(request, payload: HomePagePatchIn):
    if not request.auth.has_permission(PermissionKey.MANAGE_GUIDELINES):
        return Status(403, ErrorOut(detail="Permission denied."))
    h = HomePage.get()
    if payload.content is not None:
        h.content = payload.content
    if payload.join_content is not None:
        h.join_content = payload.join_content
    if payload.donate_url is not None:
        h.donate_url = payload.donate_url
    h.save()
    return Status(
        200,
        HomePageOut(
            content=h.content,
            join_content=h.join_content,
            donate_url=h.donate_url,
            updated_at=h.updated_at,
        ),
    )


@router.get("/pages/{slug}/", response={200: EditablePageOut, 403: ErrorOut}, auth=_optional_jwt)
def get_page(request, slug: str):
    default_vis = PageVisibility.MEMBERS_ONLY if slug == "volunteer" else PageVisibility.PUBLIC
    page = EditablePage.get_or_create_page(slug, default_visibility=default_vis)

    if page.visibility == PageVisibility.MEMBERS_ONLY:
        if isinstance(request.auth, AnonymousUser):
            return Status(403, ErrorOut(detail="Members only."))

    return Status(
        200,
        EditablePageOut(
            slug=page.slug,
            content=page.content,
            visibility=page.visibility,
            updated_at=page.updated_at,
        ),
    )


@router.patch("/pages/{slug}/", response={200: EditablePageOut, 403: ErrorOut}, auth=JWTAuth())
def update_page(request, slug: str, payload: EditablePagePatchIn):
    if not request.auth.has_permission(PermissionKey.MANAGE_GUIDELINES):
        return Status(403, ErrorOut(detail="Permission denied."))

    default_vis = PageVisibility.MEMBERS_ONLY if slug == "volunteer" else PageVisibility.PUBLIC
    page = EditablePage.get_or_create_page(slug, default_visibility=default_vis)

    if payload.content is not None:
        page.content = payload.content
    if payload.visibility is not None:
        page.visibility = payload.visibility
    page.save()

    return Status(
        200,
        EditablePageOut(
            slug=page.slug,
            content=page.content,
            visibility=page.visibility,
            updated_at=page.updated_at,
        ),
    )


@router.post("/join-request/", response={201: JoinRequestOut, 400: ErrorOut}, auth=None)
def submit_join_request(request, payload: JoinRequestIn):
    display_name = payload.display_name.strip()
    if not display_name or not payload.why_join.strip():
        return Status(400, ErrorOut(detail="display_name and why_join are required."))
    if not DISPLAY_NAME_RE.match(display_name) or len(display_name) > 64:
        return Status(
            400,
            ErrorOut(detail="Display name must contain only letters and spaces (max 64 chars)."),
        )

    try:
        validated_phone = _validate_phone(payload.phone_number)
    except ValueError as e:
        return Status(400, ErrorOut(detail=str(e)))

    join_request = JoinRequest.objects.create(
        display_name=display_name,
        phone_number=validated_phone,
        email=payload.email,
        pronouns=payload.pronouns,
        how_they_heard=payload.how_they_heard,
        why_join=payload.why_join,
    )

    logger.info("Join request submitted by %s", display_name)

    if settings.VETTING_EMAIL:
        try:
            send_mail(
                subject=f"New PDA Join Request: {display_name}",
                message=(
                    f"Display Name: {display_name}\n"
                    f"Phone: {validated_phone}\n"
                    f"Email: {payload.email or '(not provided)'}\n"
                    f"Pronouns: {payload.pronouns}\n"
                    f"How they heard: {payload.how_they_heard}\n\n"
                    f"Why they want to join:\n{payload.why_join}"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL or "noreply@pda.org",
                recipient_list=[settings.VETTING_EMAIL],
            )
        except Exception:
            logger.exception("Failed to send vetting email for join request")

    return Status(
        201,
        JoinRequestOut(
            id=str(join_request.id),
            display_name=join_request.display_name,
            phone_number=join_request.phone_number,
            email=join_request.email,
            pronouns=join_request.pronouns,
            how_they_heard=join_request.how_they_heard,
            why_join=join_request.why_join,
            submitted_at=join_request.submitted_at,
            status=join_request.status,
        ),
    )


frontend_logger = logging.getLogger("pda.frontend")


@router.post("/error-report/", response={201: ErrorReportOut}, auth=JWTAuth())
def report_error(request, payload: ErrorReportIn):
    frontend_logger.error(
        "Frontend error: %s (context: %s)",
        payload.error,
        payload.context or "unknown",
    )
    if payload.stack_trace:
        frontend_logger.error("Stack trace: %s", payload.stack_trace)
    return Status(201, ErrorReportOut(detail="Error report received."))


@router.get("/join-requests/", response={200: list[JoinRequestOut], 403: ErrorOut}, auth=JWTAuth())
def list_join_requests(request):
    if not request.auth.has_permission(PermissionKey.APPROVE_JOIN_REQUESTS):
        return Status(403, ErrorOut(detail="Permission denied."))

    join_requests = JoinRequest.objects.all()
    return Status(
        200,
        [
            JoinRequestOut(
                id=str(jr.id),
                display_name=jr.display_name,
                phone_number=jr.phone_number,
                email=jr.email,
                pronouns=jr.pronouns,
                how_they_heard=jr.how_they_heard,
                why_join=jr.why_join,
                submitted_at=jr.submitted_at,
                status=jr.status,
            )
            for jr in join_requests
        ],
    )


@router.patch(
    "/join-requests/{id}/",
    response={200: ApproveJoinRequestOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def update_join_request_status(request, id: UUID, payload: JoinRequestStatusIn):
    from users.api import _create_user_with_role
    from users.models import User

    if not request.auth.has_permission(PermissionKey.APPROVE_JOIN_REQUESTS):
        return Status(403, ErrorOut(detail="Permission denied."))

    valid_statuses = [JoinRequestStatus.APPROVED, JoinRequestStatus.REJECTED]
    if payload.status not in valid_statuses:
        return Status(400, ErrorOut(detail=f"Status must be one of: {', '.join(valid_statuses)}."))

    try:
        join_request = JoinRequest.objects.get(id=id)
    except JoinRequest.DoesNotExist:
        return Status(404, ErrorOut(detail="Join request not found."))

    if join_request.status == JoinRequestStatus.APPROVED:
        return Status(400, ErrorOut(detail="This request has already been approved."))

    join_request.status = payload.status
    join_request.save()

    temp_password = None
    if payload.status == JoinRequestStatus.APPROVED:
        if not User.objects.filter(phone_number=join_request.phone_number).exists():
            _, temp_password = _create_user_with_role(
                join_request.phone_number,
                join_request.display_name,
                join_request.email,
                None,
            )

    return Status(
        200,
        ApproveJoinRequestOut(
            id=str(join_request.id),
            display_name=join_request.display_name,
            phone_number=join_request.phone_number,
            status=join_request.status,
            temporary_password=temp_password,
        ),
    )


def _can_see_phones(requesting_user, creator, co_host_ids: set[str]) -> bool:
    """Check if requesting user can see guest phone numbers."""
    if requesting_user is None:
        return False
    if creator is not None and requesting_user.pk == creator.pk:
        return True
    return str(requesting_user.pk) in co_host_ids


def _build_guest_list(rsvps, can_see_phones: bool) -> list[RSVPGuestOut]:
    """Build guest list with optional phone visibility."""
    return [
        RSVPGuestOut(
            user_id=str(r.user_id),
            name=r.user.display_name or r.user.phone_number,
            status=r.status,
            phone=r.user.phone_number if can_see_phones else None,
        )
        for r in rsvps
    ]


def _find_my_rsvp(rsvps, user) -> str | None:
    """Find requesting user's RSVP status."""
    if user is None:
        return None
    for r in rsvps:
        if r.user_id == user.pk:
            return r.status
    return None


def _authenticated_user(requesting_user) -> object | None:
    """Return the user if authenticated, None if anonymous."""
    if requesting_user is None or isinstance(requesting_user, AnonymousUser):
        return None
    return requesting_user


def _members_only(value, default, is_authed: bool):
    """Return value if user is authenticated, default otherwise."""
    return value if is_authed else default


def _event_out(event: Event, requesting_user=None) -> EventOut:
    co_hosts = list(event.co_hosts.all())
    creator = event.created_by
    creator_name = creator.display_name or creator.phone_number if creator else None
    auth_user = _authenticated_user(requesting_user)
    is_authed = auth_user is not None
    rsvps = (
        list(event.rsvps.select_related("user").all()) if (event.rsvp_enabled and is_authed) else []
    )
    co_host_ids = {str(u.id) for u in co_hosts}
    phones_visible = _can_see_phones(auth_user, creator, co_host_ids)
    return EventOut(
        id=str(event.id),
        title=event.title,
        description=event.description,
        start_datetime=event.start_datetime,
        end_datetime=event.end_datetime,
        location=event.location,
        whatsapp_link=_members_only(event.whatsapp_link, "", is_authed),
        partiful_link=_members_only(event.partiful_link, "", is_authed),
        other_link=_members_only(event.other_link, "", is_authed),
        rsvp_enabled=_members_only(event.rsvp_enabled, False, is_authed),
        created_by_id=str(event.created_by_id) if event.created_by_id else None,
        created_by_name=creator_name,
        co_host_ids=[str(u.id) for u in co_hosts],
        co_host_names=[u.display_name or u.phone_number for u in co_hosts],
        guests=_members_only(_build_guest_list(rsvps, phones_visible), [], is_authed),
        my_rsvp=_find_my_rsvp(rsvps, auth_user),
    )


class CheckPhoneOut(BaseModel):
    exists: bool


@router.get("/events/", response={200: list[EventOut]}, auth=_optional_jwt)
def list_events(request):
    events = (
        Event.objects.select_related("created_by").prefetch_related("co_hosts", "rsvps__user").all()
    )
    return Status(200, [_event_out(e, request.auth) for e in events])


@router.get("/events/{event_id}/", response={200: EventOut, 404: ErrorOut}, auth=_optional_jwt)
def get_event(request, event_id: UUID):
    try:
        event = (
            Event.objects.select_related("created_by")
            .prefetch_related("co_hosts", "rsvps__user")
            .get(id=event_id)
        )
    except Event.DoesNotExist:
        return Status(404, ErrorOut(detail="Event not found."))
    return Status(200, _event_out(event, request.auth))


class CheckPhoneIn(BaseModel):
    phone_number: str


@router.post("/check-phone/", response={200: CheckPhoneOut}, auth=None)
def check_phone(request, payload: CheckPhoneIn):
    try:
        normalized = _validate_phone(payload.phone_number)
    except ValueError:
        return Status(200, CheckPhoneOut(exists=False))
    exists = UserModel.objects.filter(phone_number=normalized).exists()
    return Status(200, CheckPhoneOut(exists=exists))


@router.post("/events/", response={201: EventOut, 400: ErrorOut, 403: ErrorOut}, auth=JWTAuth())
def create_event(request, payload: EventIn):
    # Any authenticated member can create events.
    # manage_events is still required for editing/deleting others' events.

    if payload.end_datetime is not None and payload.end_datetime <= payload.start_datetime:
        return Status(400, ErrorOut(detail="end_datetime must be after start_datetime."))

    event = Event.objects.create(
        title=payload.title,
        description=payload.description,
        start_datetime=payload.start_datetime,
        end_datetime=payload.end_datetime,
        location=payload.location,
        whatsapp_link=payload.whatsapp_link,
        partiful_link=payload.partiful_link,
        other_link=payload.other_link,
        rsvp_enabled=payload.rsvp_enabled,
        created_by=request.auth,
    )
    if payload.co_host_ids:
        co_hosts = UserModel.objects.filter(pk__in=payload.co_host_ids)
        event.co_hosts.set(co_hosts)
    return Status(201, _event_out(event, request.auth))


@router.patch(
    "/events/{event_id}/",
    response={200: EventOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def update_event(request, event_id: UUID, payload: EventPatchIn):
    try:
        event = Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        return Status(404, ErrorOut(detail="Event not found."))

    is_manager = request.auth.has_permission(PermissionKey.MANAGE_EVENTS)
    is_creator = event.created_by_id == request.auth.pk
    if not is_manager and not is_creator:
        return Status(403, ErrorOut(detail="Permission denied."))

    updates = payload.model_dump(exclude_unset=True)
    effective_start = updates.get("start_datetime", event.start_datetime)
    effective_end = updates.get("end_datetime", event.end_datetime)
    if effective_end is not None and effective_end <= effective_start:
        return Status(400, ErrorOut(detail="end_datetime must be after start_datetime."))
    co_host_ids = updates.pop("co_host_ids", None)
    for field, value in updates.items():
        setattr(event, field, value)
    if co_host_ids is not None:
        co_hosts = UserModel.objects.filter(pk__in=co_host_ids)
        event.co_hosts.set(co_hosts)

    event.save()
    return Status(200, _event_out(event, request.auth))


@router.delete(
    "/events/{event_id}/", response={204: None, 403: ErrorOut, 404: ErrorOut}, auth=JWTAuth()
)
def delete_event(request, event_id: UUID):
    try:
        event = Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        return Status(404, ErrorOut(detail="Event not found."))

    is_manager = request.auth.has_permission(PermissionKey.MANAGE_EVENTS)
    is_creator = event.created_by_id == request.auth.pk
    if not is_manager and not is_creator:
        return Status(403, ErrorOut(detail="Permission denied."))

    event.delete()
    return Status(204, None)


@router.post(
    "/events/{event_id}/rsvp/",
    response={200: EventOut, 400: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def upsert_rsvp(request, event_id: UUID, payload: RSVPIn):
    try:
        event = (
            Event.objects.select_related("created_by")
            .prefetch_related("co_hosts", "rsvps__user")
            .get(id=event_id)
        )
    except Event.DoesNotExist:
        return Status(404, ErrorOut(detail="Event not found."))

    if not event.rsvp_enabled:
        return Status(400, ErrorOut(detail="RSVPs are not enabled for this event."))

    valid_statuses = RSVPStatus.values
    if payload.status not in valid_statuses:
        return Status(400, ErrorOut(detail=f"Status must be one of: {', '.join(valid_statuses)}."))

    EventRSVP.objects.update_or_create(
        event=event,
        user=request.auth,
        defaults={"status": payload.status},
    )
    event.refresh_from_db()
    event = (
        Event.objects.select_related("created_by")
        .prefetch_related("co_hosts", "rsvps__user")
        .get(id=event_id)
    )
    return Status(200, _event_out(event, request.auth))


@router.delete(
    "/events/{event_id}/rsvp/",
    response={204: None, 404: ErrorOut},
    auth=JWTAuth(),
)
def delete_rsvp(request, event_id: UUID):
    deleted, _ = EventRSVP.objects.filter(event_id=event_id, user=request.auth).delete()
    if not deleted:
        return Status(404, ErrorOut(detail="RSVP not found."))
    return Status(204, None)


# ---------------------------------------------------------------------------
# WhatsApp configuration (admin only)
# ---------------------------------------------------------------------------


class WhatsAppConfigOut(BaseModel):
    bot_url: str
    group_id: str
    has_secret: bool  # Don't expose the secret value, just whether it's set


class WhatsAppConfigPatchIn(BaseModel):
    bot_url: str | None = None
    bot_secret: str | None = None
    group_id: str | None = None


class WhatsAppStatusOut(BaseModel):
    connected: bool


@router.get(
    "/whatsapp/config/",
    response={200: WhatsAppConfigOut, 403: ErrorOut},
    auth=JWTAuth(),
)
def get_whatsapp_config(request):
    if not request.auth.has_permission(PermissionKey.MANAGE_WHATSAPP):
        return Status(403, ErrorOut(detail="Permission denied."))
    config = WhatsAppConfig.get()
    return Status(
        200,
        WhatsAppConfigOut(
            bot_url=config.bot_url,
            group_id=config.group_id,
            has_secret=bool(config.bot_secret),
        ),
    )


@router.patch(
    "/whatsapp/config/",
    response={200: WhatsAppConfigOut, 403: ErrorOut},
    auth=JWTAuth(),
)
def update_whatsapp_config(request, payload: WhatsAppConfigPatchIn):
    if not request.auth.has_permission(PermissionKey.MANAGE_WHATSAPP):
        return Status(403, ErrorOut(detail="Permission denied."))
    config = WhatsAppConfig.get()
    if payload.bot_url is not None:
        config.bot_url = payload.bot_url
    if payload.bot_secret is not None:
        config.bot_secret = payload.bot_secret
    if payload.group_id is not None:
        config.group_id = payload.group_id
    config.save()
    return Status(
        200,
        WhatsAppConfigOut(
            bot_url=config.bot_url,
            group_id=config.group_id,
            has_secret=bool(config.bot_secret),
        ),
    )


@router.get(
    "/whatsapp/status/",
    response={200: WhatsAppStatusOut, 403: ErrorOut},
    auth=JWTAuth(),
)
def get_whatsapp_status(request):
    if not request.auth.has_permission(PermissionKey.MANAGE_WHATSAPP):
        return Status(403, ErrorOut(detail="Permission denied."))
    config = WhatsAppConfig.get()
    bot_url = config.bot_url or getattr(settings, "WHATSAPP_BOT_URL", "")
    if not bot_url:
        return Status(200, WhatsAppStatusOut(connected=False))
    try:
        import urllib.request as _urllib

        req = _urllib.Request(
            bot_url.rstrip("/") + "/status",
            headers={
                "X-Bot-Secret": config.bot_secret or getattr(settings, "WHATSAPP_BOT_SECRET", "")
            },
        )
        with _urllib.urlopen(req, timeout=5) as resp:
            import json as _json

            data = _json.loads(resp.read())
            return Status(200, WhatsAppStatusOut(connected=bool(data.get("connected"))))
    except Exception:
        return Status(200, WhatsAppStatusOut(connected=False))
