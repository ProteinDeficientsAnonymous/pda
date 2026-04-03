"""User management endpoints (admin CRUD, roles, magic links)."""

import re

from django.db import models as dj_models
from ninja import Router
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth

from users._helpers import (
    _create_magic_token,
    _create_user_with_role,
    _is_last_admin,
    _validate_admin_role_change,
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
    ResetPasswordOut,
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
        return Status(403, ErrorOut(detail="Permission denied."))

    try:
        user, magic_token = _create_user_with_role(
            payload.phone_number, payload.display_name, payload.email, payload.role_id
        )
    except ValueError as e:
        return Status(400, ErrorOut(detail=str(e)))

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

    return Status(
        200,
        BulkUserCreateOut(results=results, created=created, failed=failed),
    )


@router.get("/users/search/", response={200: list[UserSearchOut]}, auth=JWTAuth())
def search_users(request, q: str = ""):
    qs = User.objects.filter(is_active=True, is_paused=False).exclude(pk=request.auth.pk)
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
        return Status(403, ErrorOut(detail="Permission denied."))
    users = User.objects.prefetch_related("roles").order_by("phone_number")
    return Status(200, [UserOut.from_user(u) for u in users])


@router.patch(
    "/users/{user_id}/",
    response={200: UserOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def update_user(request, user_id: str, payload: UserPatchIn):
    if not request.auth.has_permission(PermissionKey.MANAGE_USERS):
        return Status(403, ErrorOut(detail="Permission denied."))
    try:
        user = User.objects.prefetch_related("roles").get(pk=user_id)
    except User.DoesNotExist:
        return Status(404, ErrorOut(detail="User not found."))

    err = _apply_user_patch(user, user_id, payload, requester_id=str(request.auth.pk))
    if err:
        return Status(400, ErrorOut(detail=err))
    user.save()
    return Status(200, UserOut.from_user(user))


def _apply_user_patch(
    user: User, user_id: str, payload: UserPatchIn, requester_id: str
) -> str | None:
    """Apply UserPatchIn fields to user. Returns an error message string on failure, else None."""
    if payload.phone_number is not None:
        if User.objects.exclude(pk=user_id).filter(phone_number=payload.phone_number).exists():
            return "A user with that phone number already exists."
        try:
            user.phone_number = _validate_phone(payload.phone_number)
        except ValueError as e:
            return str(e)
    if payload.display_name is not None:
        user.display_name = payload.display_name
    if payload.email is not None:
        user.email = payload.email
    if payload.is_paused and requester_id == str(user.pk):
        return "You cannot pause your own account."
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
        return Status(403, ErrorOut(detail="Permission denied."))
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Status(404, ErrorOut(detail="User not found."))
    if str(user.pk) == str(request.auth.pk):
        return Status(400, ErrorOut(detail="You cannot delete your own account."))
    if _is_last_admin(user):
        return Status(400, ErrorOut(detail="Cannot delete the last admin."))
    user.delete()
    return Status(204, None)


@router.patch(
    "/users/{user_id}/roles/",
    response={200: UserOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def update_user_roles(request, user_id: str, payload: UserRolesIn):
    if not request.auth.has_permission(PermissionKey.MANAGE_USERS):
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

    user.roles.set(roles)
    user = User.objects.prefetch_related("roles").get(pk=user.pk)
    return Status(200, UserOut.from_user(user))


@router.post(
    "/users/{user_id}/magic-link/",
    response={200: ResetPasswordOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def generate_magic_link(request, user_id: str):
    if not request.auth.has_permission(PermissionKey.MANAGE_USERS):
        return Status(403, ErrorOut(detail="Permission denied."))
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Status(404, ErrorOut(detail="User not found."))
    magic_token = _create_magic_token(user)
    return Status(
        200,
        ResetPasswordOut(
            detail="Magic login link generated.",
            magic_link_token=magic_token,
        ),
    )


@router.post(
    "/users/{user_id}/reset-password/",
    response={200: ResetPasswordOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def reset_password(request, user_id: str):
    if not request.auth.has_permission(PermissionKey.MANAGE_USERS):
        return Status(403, ErrorOut(detail="Permission denied."))
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Status(404, ErrorOut(detail="User not found."))
    user.set_unusable_password()
    user.needs_onboarding = True
    user.save()
    magic_token = _create_magic_token(user)
    return Status(
        200,
        ResetPasswordOut(
            detail="Password reset. Share the magic login link with the user.",
            magic_link_token=magic_token,
        ),
    )
