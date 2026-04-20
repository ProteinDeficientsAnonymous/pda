"""User management endpoints (admin CRUD + roles)."""

import logging
import re

from community._shared import validate_display_name
from config.audit import audit_log
from django.db import models as dj_models
from django.utils import timezone
from ninja import Router
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth

from users._helpers import (
    _create_magic_token,
    _create_user_with_role,
    _is_admin,
    _is_last_admin,
    _validate_admin_role_change,
    _validate_member_role_required,
    _validate_phone,
)
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role
from users.schemas import (
    BulkUserCreateIn,
    BulkUserCreateOut,
    BulkUserResult,
    ErrorOut,
    UserCreateIn,
    UserCreateOut,
    UserOut,
    UserPatchIn,
    UserRolesIn,
    UserSearchOut,
)

router = Router()


@router.post(
    "/create-user/",
    response={201: UserCreateOut, 400: ErrorOut, 403: ErrorOut},
    auth=JWTAuth(),
)
def create_user(request, payload: UserCreateIn):
    if not request.auth.has_permission(PermissionKey.CREATE_USER):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            details={"endpoint": "create_user", "required_permission": PermissionKey.CREATE_USER},
        )
        return Status(403, ErrorOut(detail="Permission denied."))

    if payload.display_name:
        name_error = validate_display_name(payload.display_name)
        if name_error:
            return Status(400, ErrorOut(detail=name_error))

    try:
        user, magic_token = _create_user_with_role(
            payload.phone_number, payload.display_name, payload.email, payload.role_id
        )
    except ValueError as e:
        return Status(400, ErrorOut(detail=str(e)))

    audit_log(
        logging.INFO,
        "user_created",
        request,
        target_type="user",
        target_id=str(user.id),
        details={
            "display_name": user.display_name,
            "role_id": str(payload.role_id) if payload.role_id else None,
        },
    )
    return Status(
        201,
        UserCreateOut(
            id=str(user.id),
            phone_number=user.phone_number,
            display_name=user.display_name,
            magic_link_token=magic_token,
        ),
    )


@router.post(
    "/bulk-create-users/",
    response={200: BulkUserCreateOut, 403: ErrorOut},
    auth=JWTAuth(),
)
def bulk_create_users(request, payload: BulkUserCreateIn):
    if not request.auth.has_permission(PermissionKey.MANAGE_USERS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            details={
                "endpoint": "bulk_create_users",
                "required_permission": PermissionKey.MANAGE_USERS,
            },
        )
        return Status(403, ErrorOut(detail="Permission denied."))

    member_role = Role.objects.filter(name="member", is_default=True).first()
    results: list[BulkUserResult] = []
    created = 0
    failed = 0

    for i, raw_phone in enumerate(payload.phone_numbers):
        try:
            validated_phone = _validate_phone(raw_phone.strip())
        except ValueError as e:
            results.append(
                BulkUserResult(row=i + 1, phone_number=raw_phone, success=False, error=str(e))
            )
            failed += 1
            continue

        if User.objects.filter(phone_number=validated_phone).exists():
            results.append(
                BulkUserResult(
                    row=i + 1,
                    phone_number=raw_phone,
                    success=False,
                    error="Phone number already exists.",
                )
            )
            failed += 1
            continue

        user = User.objects.create_user(
            phone_number=validated_phone,
            needs_onboarding=True,
        )
        user.set_unusable_password()
        user.save(update_fields=["password"])
        if member_role:
            user.roles.add(member_role)

        magic_token = _create_magic_token(user)
        results.append(
            BulkUserResult(
                row=i + 1,
                phone_number=validated_phone,
                success=True,
                magic_link_token=magic_token,
            )
        )
        created += 1

    audit_log(
        logging.INFO,
        "users_bulk_created",
        request,
        details={"count_created": created, "count_failed": failed},
    )
    return Status(
        200,
        BulkUserCreateOut(results=results, created=created, failed=failed),
    )


@router.get("/users/search/", response={200: list[UserSearchOut]}, auth=JWTAuth())
def search_users(request, q: str = ""):
    qs = User.objects.filter(is_active=True, is_paused=False, archived_at__isnull=True).exclude(
        pk=request.auth.pk
    )
    q = q.strip()
    if q:
        digits = re.sub(r"\D", "", q)
        phone_q = dj_models.Q(phone_number__icontains=q)
        if digits and digits != q:
            phone_q = phone_q | dj_models.Q(phone_number__icontains=digits)
        qs = qs.filter(dj_models.Q(display_name__icontains=q) | phone_q)
    qs = qs.order_by("display_name")[:10]
    return Status(
        200,
        [
            UserSearchOut(
                id=str(u.id),
                display_name=u.display_name or u.phone_number,
                phone_number=u.phone_number,
            )
            for u in qs
        ],
    )


@router.get(
    "/users/",
    response={200: list[UserOut], 403: ErrorOut},
    auth=JWTAuth(),
)
def list_users(request):
    if not request.auth.has_permission(PermissionKey.MANAGE_USERS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            details={"endpoint": "list_users", "required_permission": PermissionKey.MANAGE_USERS},
        )
        return Status(403, ErrorOut(detail="Permission denied."))
    users = (
        User.objects.filter(archived_at__isnull=True)
        .prefetch_related("roles")
        .order_by("phone_number")
    )
    return Status(200, [UserOut.from_user(u) for u in users])


@router.patch(
    "/users/{user_id}/",
    response={200: UserOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def update_user(request, user_id: str, payload: UserPatchIn):
    if not request.auth.has_permission(PermissionKey.MANAGE_USERS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type="user",
            target_id=user_id,
            details={"endpoint": "update_user", "required_permission": PermissionKey.MANAGE_USERS},
        )
        return Status(403, ErrorOut(detail="Permission denied."))
    try:
        user = User.objects.prefetch_related("roles").get(pk=user_id)
    except User.DoesNotExist:
        return Status(404, ErrorOut(detail="User not found."))

    old_is_paused = user.is_paused
    err = _apply_user_patch(user, user_id, payload, requester_id=str(request.auth.pk))
    if err:
        return Status(400, ErrorOut(detail=err))
    user.save()

    if payload.is_paused is not None and payload.is_paused != old_is_paused:
        action = "user_paused" if payload.is_paused else "user_unpaused"
        audit_log(logging.WARNING, action, request, target_type="user", target_id=user_id)
    else:
        changed = [
            f
            for f in ("phone_number", "display_name", "email")
            if getattr(payload, f, None) is not None
        ]
        if changed:
            audit_log(
                logging.INFO,
                "user_updated",
                request,
                target_type="user",
                target_id=user_id,
                details={"fields_changed": changed},
            )

    return Status(200, UserOut.from_user(user))


def _patch_phone(user: User, user_id: str, phone_number: str) -> str | None:
    """Validate and apply a phone number change. Returns error string or None."""
    if User.objects.exclude(pk=user_id).filter(phone_number=phone_number).exists():
        return "A user with that phone number already exists."
    try:
        user.phone_number = _validate_phone(phone_number)
    except ValueError as e:
        return str(e)
    return None


def _validate_pause_change(user: User, is_paused: bool | None, requester_id: str) -> str | None:
    if not is_paused:
        return None
    if requester_id == str(user.pk):
        return "You cannot pause your own account."
    if _is_admin(user):
        return "Admins cannot be paused."
    return None


def _apply_user_patch(
    user: User, user_id: str, payload: UserPatchIn, requester_id: str
) -> str | None:
    """Apply UserPatchIn fields to user. Returns an error message string on failure, else None."""
    if payload.phone_number is not None:
        err = _patch_phone(user, user_id, payload.phone_number)
        if err:
            return err
    if payload.display_name is not None:
        err = validate_display_name(payload.display_name)
        if err:
            return err
        user.display_name = payload.display_name.strip()
    if payload.email is not None:
        user.email = payload.email
    err = _validate_pause_change(user, payload.is_paused, requester_id)
    if err:
        return err
    if payload.is_paused is not None:
        user.is_paused = payload.is_paused
    return None


@router.delete(
    "/users/{user_id}/",
    response={204: None, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def delete_user(request, user_id: str):
    if not request.auth.has_permission(PermissionKey.MANAGE_USERS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type="user",
            target_id=user_id,
            details={"endpoint": "delete_user", "required_permission": PermissionKey.MANAGE_USERS},
        )
        return Status(403, ErrorOut(detail="Permission denied."))
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Status(404, ErrorOut(detail="User not found."))
    if str(user.pk) == str(request.auth.pk):
        return Status(400, ErrorOut(detail="You cannot delete your own account."))
    if _is_last_admin(user):
        return Status(400, ErrorOut(detail="Cannot delete the last admin."))
    if user.archived_at is not None:
        return Status(400, ErrorOut(detail="User is already archived."))
    display_name = user.display_name
    user.archived_at = timezone.now()
    user.save(update_fields=["archived_at"])
    audit_log(
        logging.WARNING,
        "user_archived",
        request,
        target_type="user",
        target_id=user_id,
        details={"display_name": display_name},
    )
    return Status(204, None)


@router.patch(
    "/users/{user_id}/roles/",
    response={200: UserOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def update_user_roles(request, user_id: str, payload: UserRolesIn):
    if not request.auth.has_permission(PermissionKey.MANAGE_USERS):
        audit_log(
            logging.WARNING,
            "permission_denied",
            request,
            target_type="user",
            target_id=user_id,
            details={
                "endpoint": "update_user_roles",
                "required_permission": PermissionKey.MANAGE_USERS,
            },
        )
        return Status(403, ErrorOut(detail="Permission denied."))
    try:
        user = User.objects.prefetch_related("roles").get(pk=user_id)
    except User.DoesNotExist:
        return Status(404, ErrorOut(detail="User not found."))

    roles = list(Role.objects.filter(pk__in=payload.role_ids))
    if len(roles) != len(payload.role_ids):
        return Status(400, ErrorOut(detail="One or more role IDs not found."))

    error = _validate_admin_role_change(user, request.auth.pk, roles)
    if error:
        return Status(400, ErrorOut(detail=error))

    error = _validate_member_role_required(roles)
    if error:
        return Status(400, ErrorOut(detail=error))

    old_role_ids = [str(r.id) for r in user.roles.all()]
    user.roles.set(roles)
    new_role_ids = [str(r.id) for r in roles]
    audit_log(
        logging.WARNING,
        "user_roles_changed",
        request,
        target_type="user",
        target_id=user_id,
        details={"old_role_ids": old_role_ids, "new_role_ids": new_role_ids},
    )
    user = User.objects.prefetch_related("roles").get(pk=user.pk)
    return Status(200, UserOut.from_user(user))
