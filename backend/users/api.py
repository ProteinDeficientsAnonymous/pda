import logging
import secrets
import string

import phonenumbers
from django.db import models
from ninja import Router
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth
from ninja_jwt.tokens import RefreshToken
from pydantic import BaseModel

from users.models import User
from users.permissions import PermissionKey
from users.roles import PROTECTED_ROLE_NAMES, Role

logger = logging.getLogger("pda.auth")

router = Router()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _generate_temp_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _is_last_admin(user: User) -> bool:
    try:
        admin_role = Role.objects.get(name="admin", is_default=True)
    except Role.DoesNotExist:
        return False
    if not user.roles.filter(pk=admin_role.pk).exists():
        return False
    return admin_role.users.count() <= 1


def _validate_phone(raw: str) -> str:
    """Parse, validate, and return E.164. Raises ValueError on invalid."""
    try:
        parsed = phonenumbers.parse(raw, None)
    except phonenumbers.phonenumberutil.NumberParseException as e:
        raise ValueError(str(e)) from e
    if not phonenumbers.is_valid_number(parsed):
        raise ValueError(f"Invalid phone number: {raw}")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class LoginIn(BaseModel):
    phone_number: str
    password: str


class TokenOut(BaseModel):
    access: str
    refresh: str


class RefreshIn(BaseModel):
    refresh: str


class AccessOut(BaseModel):
    access: str


class RoleOut(BaseModel):
    id: str
    name: str
    is_default: bool
    permissions: list[str]


class UserOut(BaseModel):
    id: str
    phone_number: str
    display_name: str
    email: str = ""
    is_superuser: bool = False
    needs_onboarding: bool = False
    roles: list[RoleOut]

    @classmethod
    def from_user(cls, user: User) -> "UserOut":
        return cls(
            id=str(user.id),
            phone_number=user.phone_number,
            display_name=user.display_name,
            email=user.email or "",
            is_superuser=user.is_superuser,
            needs_onboarding=user.needs_onboarding,
            roles=[
                RoleOut(
                    id=str(r.id), name=r.name, is_default=r.is_default, permissions=r.permissions
                )
                for r in user.roles.all()
            ],
        )


class UserCreateIn(BaseModel):
    phone_number: str
    display_name: str = ""
    email: str = ""
    role_id: str | None = None


class UserCreateOut(BaseModel):
    id: str
    phone_number: str
    display_name: str
    temporary_password: str


class BulkUserCreateIn(BaseModel):
    phone_numbers: list[str]


class BulkUserResult(BaseModel):
    row: int
    phone_number: str
    success: bool
    error: str | None = None


class BulkUserCreateOut(BaseModel):
    results: list[BulkUserResult]
    created: int
    failed: int
    temporary_password: str


class UserPatchIn(BaseModel):
    phone_number: str | None = None
    display_name: str | None = None
    email: str | None = None
    is_active: bool | None = None


class MePatchIn(BaseModel):
    display_name: str | None = None
    email: str | None = None
    needs_onboarding: bool | None = None


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str


class UserRolesIn(BaseModel):
    role_ids: list[str]


class ResetPasswordOut(BaseModel):
    detail: str
    temporary_password: str


class RoleIn(BaseModel):
    name: str
    permissions: list[str] = []


class RolePatchIn(BaseModel):
    name: str | None = None
    permissions: list[str] | None = None


class ErrorOut(BaseModel):
    detail: str


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------


@router.post("/login/", response={200: TokenOut, 401: ErrorOut}, auth=None)
def login(request, payload: LoginIn):
    from django.contrib.auth import authenticate

    user = authenticate(request, username=payload.phone_number, password=payload.password)
    if user is None:
        logger.warning("Authentication failure: invalid credentials")
        return Status(401, ErrorOut(detail="Invalid credentials"))
    refresh = RefreshToken.for_user(user)
    return Status(200, TokenOut(access=str(refresh.access_token), refresh=str(refresh)))  # type: ignore


@router.post("/refresh/", response={200: AccessOut, 401: ErrorOut}, auth=None)
def refresh_token(request, payload: RefreshIn):
    try:
        refresh = RefreshToken(payload.refresh)
        return Status(200, AccessOut(access=str(refresh.access_token)))
    except Exception:
        return Status(401, ErrorOut(detail="Invalid or expired refresh token"))


@router.get("/me/", response={200: UserOut, 401: ErrorOut}, auth=JWTAuth())
def me(request):
    user = User.objects.prefetch_related("roles").get(pk=request.auth.pk)
    return Status(200, UserOut.from_user(user))


@router.patch("/me/", response={200: UserOut, 400: ErrorOut}, auth=JWTAuth())
def update_me(request, payload: MePatchIn):
    user = User.objects.prefetch_related("roles").get(pk=request.auth.pk)
    if payload.display_name is not None:
        user.display_name = payload.display_name
    if payload.email is not None:
        user.email = payload.email
    if payload.needs_onboarding is not None:
        user.needs_onboarding = payload.needs_onboarding
    user.save()
    return Status(200, UserOut.from_user(user))


class OnboardingIn(BaseModel):
    display_name: str
    new_password: str
    email: str = ""


@router.post("/complete-onboarding/", response={200: UserOut, 400: ErrorOut}, auth=JWTAuth())
def complete_onboarding(request, payload: OnboardingIn):
    if len(payload.new_password) < 8:
        return Status(400, ErrorOut(detail="New password must be at least 8 characters."))
    user = User.objects.prefetch_related("roles").get(pk=request.auth.pk)
    user.display_name = payload.display_name.strip()
    if payload.email:
        user.email = payload.email
    user.set_password(payload.new_password)
    user.needs_onboarding = False
    user.save()
    return Status(200, UserOut.from_user(user))


@router.post("/change-password/", response={200: ErrorOut, 400: ErrorOut}, auth=JWTAuth())
def change_password(request, payload: ChangePasswordIn):
    user = User.objects.get(pk=request.auth.pk)
    if not user.check_password(payload.current_password):
        return Status(400, ErrorOut(detail="Current password is incorrect."))
    if len(payload.new_password) < 8:
        return Status(400, ErrorOut(detail="New password must be at least 8 characters."))
    user.set_password(payload.new_password)
    user.save()
    return Status(200, ErrorOut(detail="Password updated successfully."))


# ---------------------------------------------------------------------------
# User management endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/create-user/",
    response={201: UserCreateOut, 400: ErrorOut, 403: ErrorOut},
    auth=JWTAuth(),
)
def create_user(request, payload: UserCreateIn):
    if not request.auth.has_permission(PermissionKey.CREATE_USER):
        return Status(403, ErrorOut(detail="Permission denied."))

    if User.objects.filter(phone_number=payload.phone_number).exists():
        return Status(400, ErrorOut(detail="A user with that phone number already exists."))

    try:
        validated_phone = _validate_phone(payload.phone_number)
    except ValueError as e:
        return Status(400, ErrorOut(detail=str(e)))

    temp_password = _generate_temp_password()
    user = User.objects.create_user(
        phone_number=validated_phone,
        password=temp_password,
        display_name=payload.display_name,
        email=payload.email,
        needs_onboarding=True,
    )

    if payload.role_id:
        try:
            role = Role.objects.get(pk=payload.role_id)
            user.roles.add(role)
        except Role.DoesNotExist:
            user.delete()
            return Status(400, ErrorOut(detail="Role not found."))
    else:
        member_role = Role.objects.filter(name="member", is_default=True).first()
        if member_role:
            user.roles.add(member_role)

    return Status(
        201,
        UserCreateOut(
            id=str(user.id),
            phone_number=user.phone_number,
            display_name=user.display_name,
            temporary_password=temp_password,
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
    temp_password = _generate_temp_password()

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
            password=temp_password,
            needs_onboarding=True,
        )
        if member_role:
            user.roles.add(member_role)

        results.append(BulkUserResult(row=i + 1, phone_number=validated_phone, success=True))
        created += 1

    return Status(
        200,
        BulkUserCreateOut(
            results=results, created=created, failed=failed, temporary_password=temp_password
        ),
    )


class UserSearchOut(BaseModel):
    id: str
    display_name: str


@router.get("/users/search/", response={200: list[UserSearchOut]}, auth=JWTAuth())
def search_users(request, q: str = ""):
    qs = User.objects.filter(is_active=True).exclude(pk=request.auth.pk)
    q = q.strip()
    if q:
        qs = qs.filter(models.Q(display_name__icontains=q) | models.Q(phone_number__icontains=q))
    qs = qs.order_by("display_name")[:10]
    return Status(
        200,
        [
            UserSearchOut(
                id=str(u.id),
                display_name=u.display_name or u.phone_number,
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

    if payload.phone_number is not None:
        if User.objects.exclude(pk=user_id).filter(phone_number=payload.phone_number).exists():
            return Status(400, ErrorOut(detail="A user with that phone number already exists."))
        try:
            user.phone_number = _validate_phone(payload.phone_number)
        except ValueError as e:
            return Status(400, ErrorOut(detail=str(e)))
    if payload.display_name is not None:
        user.display_name = payload.display_name
    if payload.email is not None:
        user.email = payload.email
    if payload.is_active is not None:
        user.is_active = payload.is_active
    user.save()
    return Status(200, UserOut.from_user(user))


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

    admin_role = Role.objects.filter(name="admin", is_default=True).first()
    if admin_role:
        if str(user.pk) == str(request.auth.pk) and user.roles.filter(pk=admin_role.pk).exists():
            if admin_role not in roles:
                return Status(400, ErrorOut(detail="You cannot remove your own admin role."))
        if _is_last_admin(user) and admin_role not in roles:
            return Status(400, ErrorOut(detail="Cannot remove admin from the last admin."))

    user.roles.set(roles)
    user = User.objects.prefetch_related("roles").get(pk=user.pk)
    return Status(200, UserOut.from_user(user))


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
    temp_password = _generate_temp_password()
    user.set_password(temp_password)
    user.save()
    return Status(
        200,
        ResetPasswordOut(
            detail="Password reset. Share the temporary password with the user.",
            temporary_password=temp_password,
        ),
    )


# ---------------------------------------------------------------------------
# Role management endpoints
# ---------------------------------------------------------------------------


@router.get("/roles/", response={200: list[RoleOut]}, auth=JWTAuth())
def list_roles(request):
    roles = Role.objects.all()
    return Status(
        200,
        [
            RoleOut(id=str(r.id), name=r.name, is_default=r.is_default, permissions=r.permissions)
            for r in roles
        ],
    )


@router.post(
    "/roles/",
    response={201: RoleOut, 400: ErrorOut, 403: ErrorOut},
    auth=JWTAuth(),
)
def create_role(request, payload: RoleIn):
    if not request.auth.has_permission(PermissionKey.MANAGE_ROLES):
        return Status(403, ErrorOut(detail="Permission denied."))
    if Role.objects.filter(name=payload.name).exists():
        return Status(400, ErrorOut(detail="A role with that name already exists."))
    role = Role.objects.create(name=payload.name, permissions=payload.permissions)
    return Status(
        201,
        RoleOut(
            id=str(role.id),
            name=role.name,
            is_default=role.is_default,
            permissions=role.permissions,
        ),
    )


@router.patch(
    "/roles/{role_id}/",
    response={200: RoleOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def update_role(request, role_id: str, payload: RolePatchIn):
    if not request.auth.has_permission(PermissionKey.MANAGE_ROLES):
        return Status(403, ErrorOut(detail="Permission denied."))
    try:
        role = Role.objects.get(pk=role_id)
    except Role.DoesNotExist:
        return Status(404, ErrorOut(detail="Role not found."))

    if payload.name is not None and payload.name != role.name:
        if role.name in PROTECTED_ROLE_NAMES:
            return Status(400, ErrorOut(detail=f"Cannot rename protected role '{role.name}'."))
        if Role.objects.exclude(pk=role_id).filter(name=payload.name).exists():
            return Status(400, ErrorOut(detail="A role with that name already exists."))
        role.name = payload.name

    if payload.permissions is not None:
        role.permissions = payload.permissions

    role.save()
    return Status(
        200,
        RoleOut(
            id=str(role.id),
            name=role.name,
            is_default=role.is_default,
            permissions=role.permissions,
        ),
    )


@router.delete(
    "/roles/{role_id}/",
    response={204: None, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def delete_role(request, role_id: str):
    if not request.auth.has_permission(PermissionKey.MANAGE_ROLES):
        return Status(403, ErrorOut(detail="Permission denied."))
    try:
        role = Role.objects.get(pk=role_id)
    except Role.DoesNotExist:
        return Status(404, ErrorOut(detail="Role not found."))
    if role.name in PROTECTED_ROLE_NAMES:
        return Status(400, ErrorOut(detail=f"Cannot delete protected role '{role.name}'."))
    if role.users.exists():
        return Status(400, ErrorOut(detail="Cannot delete a role that has users assigned."))
    role.delete()
    return Status(204, None)
