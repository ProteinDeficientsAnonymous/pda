import logging
import re
import secrets
from datetime import datetime, timedelta
from uuid import UUID

import phonenumbers
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.mail import send_mail
from django.http import HttpRequest, HttpResponse
from django.utils import timezone
from ninja import Router
from ninja.responses import Status
from ninja.security import HttpBearer
from ninja_jwt.authentication import JWTAuth, JWTBaseAuthentication
from pydantic import BaseModel, Field
from users.models import User as UserModel
from users.permissions import PermissionKey

from community.models import (
    FAQ,
    CommunityGuidelines,
    EditablePage,
    Event,
    EventRSVP,
    HomePage,
    JoinFormQuestion,
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
    answers: dict[str, str] = {}


class JoinRequestAnswerOut(BaseModel):
    question_id: str
    label: str
    answer: str


class JoinRequestOut(BaseModel):
    id: str
    display_name: str
    phone_number: str
    answers: list[JoinRequestAnswerOut] = []
    submitted_at: datetime
    status: str


class JoinFormQuestionOut(BaseModel):
    id: str
    label: str
    field_type: str
    options: list[str] = []
    required: bool
    display_order: int


class JoinFormQuestionIn(BaseModel):
    label: str
    field_type: str = "text"
    options: list[str] = []
    required: bool = False


class JoinFormQuestionOrderIn(BaseModel):
    question_ids: list[str]


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


class EventListOut(BaseModel):
    id: str
    title: str
    description: str
    start_datetime: datetime
    end_datetime: datetime | None = None
    location: str
    whatsapp_link: str = ""
    partiful_link: str = ""
    created_by_id: str | None = None
    co_host_ids: list[str] = []


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


@router.get("/faq/", response={200: GuidelinesOut}, auth=JWTAuth())
def get_faq(request):
    f = FAQ.get()
    return Status(200, GuidelinesOut(content=f.content, updated_at=f.updated_at))


@router.patch("/faq/", response={200: GuidelinesOut, 403: ErrorOut}, auth=JWTAuth())
def update_faq(request, payload: GuidelinesPatchIn):
    if not request.auth.has_permission(PermissionKey.EDIT_FAQ):
        return Status(403, ErrorOut(detail="Permission denied."))
    f = FAQ.get()
    f.content = payload.content
    f.save()
    return Status(200, GuidelinesOut(content=f.content, updated_at=f.updated_at))


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
    if not request.auth.has_permission(PermissionKey.EDIT_HOMEPAGE):
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


def _join_request_out(jr: JoinRequest) -> JoinRequestOut:
    answers = [
        JoinRequestAnswerOut(question_id=qid, label=data["label"], answer=data["answer"])
        for qid, data in (jr.custom_answers or {}).items()
    ]
    return JoinRequestOut(
        id=str(jr.id),
        display_name=jr.display_name,
        phone_number=jr.phone_number,
        answers=answers,
        submitted_at=jr.submitted_at,
        status=jr.status,
    )


# ---------------------------------------------------------------------------
# Join form configuration
# ---------------------------------------------------------------------------


@router.get("/join-form/", response={200: list[JoinFormQuestionOut]}, auth=None)
def get_join_form(request):
    questions = JoinFormQuestion.objects.all()
    return Status(
        200,
        [
            JoinFormQuestionOut(
                id=str(q.id),
                label=q.label,
                field_type=q.field_type,
                options=q.options or [],
                required=q.required,
                display_order=q.display_order,
            )
            for q in questions
        ],
    )


@router.post(
    "/join-form/questions/",
    response={201: JoinFormQuestionOut, 403: ErrorOut},
    auth=JWTAuth(),
)
def create_join_form_question(request, payload: JoinFormQuestionIn):
    if not request.auth.has_permission(PermissionKey.EDIT_JOIN_QUESTIONS):
        return Status(403, ErrorOut(detail="Permission denied."))
    max_order = JoinFormQuestion.objects.count()
    q = JoinFormQuestion.objects.create(
        label=payload.label,
        field_type=payload.field_type,
        options=payload.options,
        required=payload.required,
        display_order=max_order,
    )
    return Status(
        201,
        JoinFormQuestionOut(
            id=str(q.id),
            label=q.label,
            field_type=q.field_type,
            options=q.options or [],
            required=q.required,
            display_order=q.display_order,
        ),
    )


@router.patch(
    "/join-form/questions/{question_id}/",
    response={200: JoinFormQuestionOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def update_join_form_question(request, question_id: UUID, payload: JoinFormQuestionIn):
    if not request.auth.has_permission(PermissionKey.EDIT_JOIN_QUESTIONS):
        return Status(403, ErrorOut(detail="Permission denied."))
    try:
        q = JoinFormQuestion.objects.get(id=question_id)
    except JoinFormQuestion.DoesNotExist:
        return Status(404, ErrorOut(detail="Question not found."))
    q.label = payload.label
    q.field_type = payload.field_type
    q.options = payload.options
    q.required = payload.required
    q.save()
    return Status(
        200,
        JoinFormQuestionOut(
            id=str(q.id),
            label=q.label,
            field_type=q.field_type,
            options=q.options or [],
            required=q.required,
            display_order=q.display_order,
        ),
    )


@router.delete(
    "/join-form/questions/{question_id}/",
    response={204: None, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def delete_join_form_question(request, question_id: UUID):
    if not request.auth.has_permission(PermissionKey.EDIT_JOIN_QUESTIONS):
        return Status(403, ErrorOut(detail="Permission denied."))
    try:
        q = JoinFormQuestion.objects.get(id=question_id)
    except JoinFormQuestion.DoesNotExist:
        return Status(404, ErrorOut(detail="Question not found."))
    q.delete()
    return Status(204, None)


@router.put(
    "/join-form/questions/order/",
    response={200: list[JoinFormQuestionOut], 403: ErrorOut},
    auth=JWTAuth(),
)
def reorder_join_form_questions(request, payload: JoinFormQuestionOrderIn):
    if not request.auth.has_permission(PermissionKey.EDIT_JOIN_QUESTIONS):
        return Status(403, ErrorOut(detail="Permission denied."))
    for idx, qid in enumerate(payload.question_ids):
        JoinFormQuestion.objects.filter(id=qid).update(display_order=idx)
    questions = JoinFormQuestion.objects.all()
    return Status(
        200,
        [
            JoinFormQuestionOut(
                id=str(q.id),
                label=q.label,
                field_type=q.field_type,
                options=q.options or [],
                required=q.required,
                display_order=q.display_order,
            )
            for q in questions
        ],
    )


# ---------------------------------------------------------------------------
# Join request submission
# ---------------------------------------------------------------------------


def _validate_answers(
    answers: dict[str, str],
    questions: dict[str, JoinFormQuestion],
) -> str | None:
    """Validate answers against questions. Returns error message or None."""
    for q_id, q in questions.items():
        answer = answers.get(q_id, "").strip()
        if q.required and not answer:
            return f'"{q.label}" is required.'
        if q.field_type == "select" and answer and answer not in (q.options or []):
            return f'Invalid option for "{q.label}".'
    return None


def _build_custom_answers(
    answers: dict[str, str],
    questions: dict[str, JoinFormQuestion],
) -> dict:
    """Snapshot answers with their labels."""
    result = {}
    for q_id, q in questions.items():
        answer = answers.get(q_id, "").strip()
        if answer:
            result[q_id] = {"label": q.label, "answer": answer}
    return result


def _send_join_request_email(display_name: str, phone: str, custom_answers: dict) -> None:
    """Send vetting email for a new join request."""
    if not settings.VETTING_EMAIL:
        return
    try:
        answer_lines = "\n".join(
            f"{data['label']}: {data['answer']}" for data in custom_answers.values()
        )
        send_mail(
            subject=f"New PDA Join Request: {display_name}",
            message=f"Display Name: {display_name}\nPhone: {phone}\n\n{answer_lines}",
            from_email=settings.DEFAULT_FROM_EMAIL or "noreply@pda.org",
            recipient_list=[settings.VETTING_EMAIL],
        )
    except Exception:
        logger.exception("Failed to send vetting email for join request")


@router.post("/join-request/", response={201: JoinRequestOut, 400: ErrorOut}, auth=None)
def submit_join_request(request, payload: JoinRequestIn):
    display_name = payload.display_name.strip()
    if not display_name:
        return Status(400, ErrorOut(detail="display_name is required."))
    if not DISPLAY_NAME_RE.match(display_name) or len(display_name) > 64:
        return Status(
            400,
            ErrorOut(detail="Display name must contain only letters and spaces (max 64 chars)."),
        )

    try:
        validated_phone = _validate_phone(payload.phone_number)
    except ValueError as e:
        return Status(400, ErrorOut(detail=str(e)))

    questions = {str(q.id): q for q in JoinFormQuestion.objects.all()}
    error = _validate_answers(payload.answers, questions)
    if error:
        return Status(400, ErrorOut(detail=error))

    custom_answers = _build_custom_answers(payload.answers, questions)

    join_request = JoinRequest.objects.create(
        display_name=display_name,
        phone_number=validated_phone,
        custom_answers=custom_answers,
    )

    logger.info("Join request submitted by %s", display_name)
    _send_join_request_email(display_name, validated_phone, custom_answers)

    return Status(201, _join_request_out(join_request))


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
    return Status(200, [_join_request_out(jr) for jr in join_requests])


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
                "",
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
    rsvps = list(event.rsvps.all()) if (event.rsvp_enabled and is_authed) else []
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


@router.get("/events/", response={200: list[EventListOut]}, auth=_optional_jwt)
def list_events(request):
    is_authed = not isinstance(request.auth, AnonymousUser)
    events = Event.objects.select_related("created_by").prefetch_related("co_hosts").all()
    return Status(
        200,
        [
            EventListOut(
                id=str(e.id),
                title=e.title,
                description=e.description,
                start_datetime=e.start_datetime,
                end_datetime=e.end_datetime,
                location=e.location,
                whatsapp_link=_members_only(e.whatsapp_link, "", is_authed),
                partiful_link=_members_only(e.partiful_link, "", is_authed),
                created_by_id=str(e.created_by_id) if e.created_by_id else None,
                co_host_ids=[str(c.id) for c in e.co_hosts.all()],
            )
            for e in events
        ],
    )


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
# Calendar feed (subscribable .ics)
# ---------------------------------------------------------------------------


class CalendarTokenOut(BaseModel):
    token: str
    feed_url: str


def _build_feed_url(request: HttpRequest, token: str) -> str:
    return request.build_absolute_uri(f"/api/community/calendar/feed/?token={token}")


@router.get("/calendar/token/", response={200: CalendarTokenOut}, auth=JWTAuth())
def get_calendar_token(request):
    user = request.auth
    return Status(
        200,
        CalendarTokenOut(
            token=user.calendar_token,
            feed_url=_build_feed_url(request, user.calendar_token) if user.calendar_token else "",
        ),
    )


@router.post("/calendar/token/", response={200: CalendarTokenOut}, auth=JWTAuth())
def generate_calendar_token(request):
    user = request.auth
    user.calendar_token = secrets.token_urlsafe(32)
    user.save(update_fields=["calendar_token"])
    return Status(
        200,
        CalendarTokenOut(
            token=user.calendar_token,
            feed_url=_build_feed_url(request, user.calendar_token),
        ),
    )


@router.get("/calendar/feed/", auth=None)
def calendar_feed(request, token: str = ""):
    if not token:
        return HttpResponse("Missing token.", status=403, content_type="text/plain")

    try:
        user = UserModel.objects.get(calendar_token=token)
    except UserModel.DoesNotExist:
        return HttpResponse("Invalid token.", status=403, content_type="text/plain")

    # Ignore tokens that are empty strings (not yet generated)
    if not user.calendar_token:
        return HttpResponse("Invalid token.", status=403, content_type="text/plain")

    import icalendar

    cal = icalendar.Calendar()
    cal.add("prodid", "-//PDA//PDA Calendar//EN")
    cal.add("version", "2.0")
    cal.add("x-wr-calname", "PDA Events")

    cutoff = timezone.now() - timedelta(days=30)
    events = (
        Event.objects.filter(start_datetime__gte=cutoff)
        .select_related("created_by")
        .order_by("start_datetime")
    )

    for event in events:
        vevent = icalendar.Event()
        vevent.add("uid", f"{event.id}@pda")
        vevent.add("dtstamp", timezone.now())
        vevent.add("dtstart", event.start_datetime)
        vevent.add(
            "dtend",
            event.end_datetime or event.start_datetime + timedelta(hours=2),
        )
        vevent.add("summary", event.title)
        desc_parts = []
        if event.description:
            desc_parts.append(event.description)
        if event.whatsapp_link:
            desc_parts.append(f"WhatsApp: {event.whatsapp_link}")
        if event.partiful_link:
            desc_parts.append(f"Partiful: {event.partiful_link}")
        if event.other_link:
            desc_parts.append(f"Link: {event.other_link}")
        if desc_parts:
            vevent.add("description", "\n".join(desc_parts))
        if event.location:
            vevent.add("location", event.location)
        cal.add_component(vevent)

    response = HttpResponse(cal.to_ical(), content_type="text/calendar")
    response["Content-Disposition"] = 'inline; filename="pda-calendar.ics"'
    return response


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
