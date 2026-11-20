"""User management endpoints (admin CRUD + roles)."""

import logging
import re

from community.attendance.analytics import AttendedEventOut
from community.events.limited_access import is_limited
from community.models import AttendanceStatus, EventRSVP
from community.rsvps.counts import attendance_q, reportable_events_q
from community.validation import Code, InvalidStateTransition, TransitionFailure, raise_validation
from config.audit import AuditTarget, AuditTargetType, audit_log
from config.auth import gated_jwt
from django.db import models as dj_models
from django.db import transaction
from ninja import Router
from ninja.responses import Status

from users._attendance_pause import apply_attendance_pause_patch, release_held_events
from users._unpause import email_unpaused
from users.helpers import (
    check_and_set_email,
    is_admin,
    resolve_name_fields,
    validate_admin_role_change,
    validate_member_role_required,
    visible_name,
)
from users.models import MembershipEvent, MembershipStatus, User
from users.permissions import PermissionKey
from users.phone import ADMIN_ENTERED_PHONE_REGION, validate_phone
from users.roles import Role
from users.schemas import (
    ErrorOut,
    UserOut,
    UserPatchIn,
    UserRolesIn,
    UserSearchOut,
)

router = Router()


def _require_permission(
    request, key: PermissionKey, endpoint: str, user_id: str | None = None
) -> None:
    if request.auth.has_permission(key):
        return
    details = {"endpoint": endpoint, "required_permission": key}
    target = (
        AuditTarget(details=details)
        if user_id is None
        else AuditTarget(type=AuditTargetType.USER, id=user_id, details=details)
    )
    audit_log(logging.WARNING, "permission_denied", request, persist=False, target=target)
    raise_validation(Code.Perm.DENIED, status_code=403, action=endpoint)


def require_manage_users(request, endpoint: str, user_id: str | None = None) -> None:
    _require_permission(request, PermissionKey.MANAGE_USERS, endpoint, user_id)


def _matches_for_non_admin(u: User, q: str, digits: str) -> bool:
    """Whether a search hit is legitimate for a non-admin viewer.

    The DB query matches on last_name too, so a hide_last_name user would
    otherwise leak via search even though their last name is suppressed in the
    response. Re-check the match here against only the fields a non-admin can
    actually see (first name, phone).
    """
    if not u.hide_last_name:
        return True
    if q.lower() in u.first_name.lower():
        return True
    return bool(u.show_phone and (q in u.phone_number or (digits and digits in u.phone_number)))


def _search_queryset(viewer: User, q: str, digits: str):
    qs = User.objects.active_members().filter(needs_onboarding=False).exclude(pk=viewer.pk)
    if q:
        phone_q = dj_models.Q(phone_number__icontains=q)
        if digits and digits != q:
            phone_q = phone_q | dj_models.Q(phone_number__icontains=digits)
        name_q = dj_models.Q(first_name__icontains=q) | dj_models.Q(last_name__icontains=q)
        qs = qs.filter(name_q | phone_q)
    return qs.order_by("first_name", "last_name")


@router.get("/users/search/", response={200: list[UserSearchOut], 403: ErrorOut}, auth=gated_jwt)
def search_users(request, q: str = ""):
    if is_limited(request.auth):
        raise_validation(Code.Perm.DENIED, status_code=403, action="search_users")
    q = q.strip()
    digits = re.sub(r"\D", "", q)
    qs = _search_queryset(request.auth, q, digits)
    needs_non_admin_filter = bool(q) and not is_admin(request.auth)
    # Non-admins post-filter in Python (the DB can match a hidden last name),
    # so fetch some headroom before capping to 10. Admins take the top 10
    # straight from the DB.
    users = list(qs[:200]) if needs_non_admin_filter else list(qs[:10])
    if needs_non_admin_filter:
        users = [u for u in users if _matches_for_non_admin(u, q, digits)][:10]
    results = []
    for u in users:
        last_name, full_name = visible_name(u, request.auth)
        results.append(
            UserSearchOut(
                id=str(u.id),
                first_name=u.first_name,
                last_name=last_name,
                full_name=full_name,
                # Respect each member's privacy flag — blank the phone rather
                # than dropping the field, so callers (co-host/invite picker)
                # don't break on a missing key. Mirrors the member directory.
                phone_number=u.phone_number if u.show_phone else "",
            )
        )
    return Status(200, results)


@router.get(
    "/users/",
    response={200: list[UserOut], 403: ErrorOut},
    auth=gated_jwt,
)
def list_users(request, include_non_members: bool = False):
    require_manage_users(request, "list_users")
    # shares attendance_q + reportable_events_q with the report so the surfaces can't drift.
    attended = attendance_q(AttendanceStatus.ATTENDED, prefix="event_rsvps")
    reportable = reportable_events_q(prefix="event_rsvps__event")
    # The opt-in adds public-RSVP non-members.
    base = User.objects.all() if include_non_members else User.objects.managed()
    users = (
        base.filter(archived_at__isnull=True)
        .prefetch_related("roles")
        .annotate(
            last_attended=dj_models.Max(
                "event_rsvps__event__start_datetime",
                filter=attended & reportable,
            ),
            attended_count=dj_models.Count(
                "event_rsvps__event",
                filter=attended & reportable,
                distinct=True,
            ),
        )
        .order_by("phone_number")
    )
    return Status(200, [UserOut.from_user(u) for u in users])


@router.get(
    "/users/{user_id}/attended-events/",
    response={200: list[AttendedEventOut], 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def list_member_attended_events(request, user_id: str):
    require_manage_users(request, "list_member_attended_events", user_id)
    if not User.objects.filter(pk=user_id, archived_at__isnull=True).exists():
        raise_validation(Code.User.NOT_FOUND, status_code=404)
    rsvps = (
        EventRSVP.objects.filter(
            reportable_events_q(), user_id=user_id, attendance=AttendanceStatus.ATTENDED
        )
        .select_related("event")
        .order_by("-event__start_datetime")
    )
    return Status(200, [AttendedEventOut.from_rsvp(r) for r in rsvps])


@router.patch(
    "/users/{user_id}/",
    response={200: UserOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut, 409: ErrorOut},
    auth=gated_jwt,
)
def update_user(request, user_id: str, payload: UserPatchIn):
    require_manage_users(request, "update_user", user_id)
    editable = User.objects.members_or_archived().prefetch_related("roles")
    with transaction.atomic():
        try:
            # Row lock: concurrent pause/archive can't overwrite a stale in-memory status.
            user = editable.select_for_update().get(pk=user_id)
        except User.DoesNotExist:
            raise_validation(Code.User.NOT_FOUND, status_code=404)

        was_guidelines_paused = user.is_guidelines_paused
        before_status = str(
            user.status_before_archive if user.is_archived else user.membership_status
        )
        _apply_user_patch(user, user_id, payload, requester=request.auth)
        user.save()
        pause_details = _pause_transition_details(
            request, user, payload, was_guidelines_paused, before_status
        )
        _audit_user_update(request, user_id, payload, pause_details)
    if apply_attendance_pause_patch(request, user, payload.attendance_paused):
        user = editable.get(pk=user_id)
    if was_guidelines_paused and not user.is_guidelines_paused:
        email_unpaused(user)
    return Status(200, UserOut.from_user(user))


def _pause_transition_details(
    request,
    user: User,
    payload: UserPatchIn,
    was_guidelines_paused: bool,
    before_status: str,
) -> dict | None:
    if payload.guidelines_paused is None or payload.guidelines_paused == was_guidelines_paused:
        return None
    released = (
        release_held_events(request, user, MembershipStatus.GUIDELINES_PAUSED)[1]
        if payload.guidelines_paused
        else {}
    )
    event = (
        MembershipEvent.PAUSE_FOR_GUIDELINES
        if payload.guidelines_paused
        else MembershipEvent.LIFT_GUIDELINES_PAUSE
    )
    after_status = str(user.status_before_archive if user.is_archived else user.membership_status)
    return {
        "full_name": user.full_name,
        "event": event,
        "from": before_status,
        "to": after_status,
        **released,
    }


def _audit_user_update(
    request, user_id: str, payload: UserPatchIn, pause_details: dict | None
) -> None:
    """Log user_paused/user_unpaused for a guidelines-pause change and user_updated for edits."""
    if pause_details is not None:
        action = "user_paused" if payload.guidelines_paused else "user_unpaused"
        audit_log(
            logging.WARNING,
            action,
            request,
            target=AuditTarget(type=AuditTargetType.USER, id=user_id, details=pause_details),
        )

    changed = [
        f
        for f in ("phone_number", "first_name", "last_name", "email", "has_joined_whatsapp")
        if getattr(payload, f, None) is not None
    ]
    if changed:
        audit_log(
            logging.INFO,
            "user_updated",
            request,
            target=AuditTarget(
                type=AuditTargetType.USER, id=user_id, details={"fields_changed": changed}
            ),
        )


def _patch_phone(user: User, user_id: str, phone_number: str) -> None:
    """Validate and apply a phone number change. Raises ValidationException on failure."""
    if User.objects.exclude(pk=user_id).filter(phone_number=phone_number).exists():
        raise_validation(Code.Phone.ALREADY_EXISTS, field="phone_number", status_code=409)
    user.phone_number = validate_phone(phone_number, ADMIN_ENTERED_PHONE_REGION)


def _validate_pause_change(
    user: User, paused: bool | None, requester_id: str, event: MembershipEvent
) -> None:
    if not paused:
        return
    to_status = (
        MembershipStatus.GUIDELINES_PAUSED
        if event == MembershipEvent.PAUSE_FOR_GUIDELINES
        else MembershipStatus.ATTENDANCE_PAUSED
    )
    failure = TransitionFailure(
        action="user_transition_rejected",
        target_type=AuditTargetType.USER,
        target_id=str(user.pk),
        event=event,
        from_status=str(user.membership_status),
        to_status=to_status,
    )
    if requester_id == str(user.pk):
        raise InvalidStateTransition(Code.User.CANNOT_PAUSE_SELF, failure)
    if is_admin(user):
        raise InvalidStateTransition(Code.User.CANNOT_PAUSE_ADMIN, failure)


def _apply_user_patch(user: User, user_id: str, payload: UserPatchIn, requester: User) -> None:
    """Apply UserPatchIn fields to user. Raises ValidationException on invalid input."""
    requester_id = str(requester.pk)
    if payload.phone_number is not None:
        _patch_phone(user, user_id, payload.phone_number)
    resolve_name_fields(user, payload)
    if payload.email is not None:
        check_and_set_email(user, payload.email, exclude_pk=user_id)
    _validate_pause_change(
        user, payload.guidelines_paused, requester_id, MembershipEvent.PAUSE_FOR_GUIDELINES
    )
    _validate_pause_change(
        user, payload.attendance_paused, requester_id, MembershipEvent.PAUSE_FOR_ATTENDANCE
    )
    # WhatsApp before pause toggles so a pause in the same PATCH still clears it.
    if payload.has_joined_whatsapp is not None:
        user.has_joined_whatsapp = payload.has_joined_whatsapp
    # Attendance lift check uses pre-toggle state; lifting guidelines lands on attendance pause.
    if payload.attendance_paused is False and user.is_attendance_paused:
        user.lift_attendance_pause(by=requester)
    if (
        payload.guidelines_paused is not None
        and payload.guidelines_paused != user.is_guidelines_paused
    ):
        _toggle_guidelines_pause(user, payload.guidelines_paused, by=requester)
    if payload.attendance_paused and user.is_guidelines_paused:
        user.apply_attendance_pause(by=requester)


def _toggle_guidelines_pause(user: User, paused: bool, *, by: User) -> None:
    if paused:
        user.apply_guidelines_pause(by=by)
    else:
        user.lift_guidelines_pause(by=by)


@router.patch(
    "/users/{user_id}/roles/",
    response={200: UserOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=gated_jwt,
)
def update_user_roles(request, user_id: str, payload: UserRolesIn):
    require_manage_users(request, "update_user_roles", user_id)
    # Attendance-paused users can still sign in, so they can't gain roles until unpaused.
    assignable = User.objects.members_or_archived().exclude(
        membership_status=MembershipStatus.ATTENDANCE_PAUSED
    )
    try:
        user = assignable.prefetch_related("roles").get(pk=user_id)
    except User.DoesNotExist:
        raise_validation(Code.User.NOT_FOUND, status_code=404)

    roles = list(Role.objects.filter(pk__in=payload.role_ids))
    if len(roles) != len(payload.role_ids):
        raise_validation(Code.User.ROLE_IDS_NOT_FOUND, field="role_ids", status_code=400)

    validate_admin_role_change(user, request.auth, roles)
    validate_member_role_required(roles)

    old_role_ids = [str(r.id) for r in user.roles.all()]
    user.roles.set(roles)
    new_role_ids = [str(r.id) for r in roles]
    audit_log(
        logging.WARNING,
        "user_roles_changed",
        request,
        target=AuditTarget(
            type=AuditTargetType.USER,
            id=user_id,
            details={"old_role_ids": old_role_ids, "new_role_ids": new_role_ids},
        ),
    )
    user = User.objects.members_or_archived().prefetch_related("roles").get(pk=user.pk)
    return Status(200, UserOut.from_user(user))
