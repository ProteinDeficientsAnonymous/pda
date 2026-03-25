import secrets
import string

from ninja import Router
from ninja_jwt.authentication import JWTAuth
from ninja_jwt.tokens import RefreshToken
from pydantic import BaseModel

from users.models import User
from users.permissions import PermissionKey
from users.roles import PROTECTED_ROLE_NAMES, Role

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


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class LoginIn(BaseModel):
    email: str
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
    email: str
    first_name: str
    last_name: str
    roles: list[RoleOut]

    @classmethod
    def from_user(cls, user: User) -> "UserOut":
        return cls(
            id=str(user.id),
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            roles=[
                RoleOut(id=str(r.id), name=r.name, is_default=r.is_default, permissions=r.permissions)
                for r in user.roles.all()
            ],
        )


class UserCreateIn(BaseModel):
    email: str
    first_name: str = ""
    last_name: str = ""
    role_id: str | None = None


class UserCreateOut(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    temporary_password: str


class UserPatchIn(BaseModel):
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    is_active: bool | None = None


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

    user = authenticate(request, username=payload.email, password=payload.password)
    if user is None:
        return 401, ErrorOut(detail="Invalid credentials")
    refresh = RefreshToken.for_user(user)
    return 200, TokenOut(access=str(refresh.access_token), refresh=str(refresh))


@router.post("/refresh/", response={200: AccessOut, 401: ErrorOut}, auth=None)
def refresh_token(request, payload: RefreshIn):
    try:
        refresh = RefreshToken(payload.refresh)
        return 200, AccessOut(access=str(refresh.access_token))
    except Exception:
        return 401, ErrorOut(detail="Invalid or expired refresh token")


@router.get("/me/", response={200: UserOut, 401: ErrorOut}, auth=JWTAuth())
def me(request):
    user = User.objects.prefetch_related("roles").get(pk=request.auth.pk)
    return 200, UserOut.from_user(user)


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
        return 403, ErrorOut(detail="Permission denied.")

    if User.objects.filter(email=payload.email).exists():
        return 400, ErrorOut(detail="A user with that email already exists.")

    temp_password = _generate_temp_password()
    user = User.objects.create_user(
        email=payload.email,
        password=temp_password,
        first_name=payload.first_name,
        last_name=payload.last_name,
    )

    if payload.role_id:
        try:
            role = Role.objects.get(pk=payload.role_id)
            user.roles.add(role)
        except Role.DoesNotExist:
            user.delete()
            return 400, ErrorOut(detail="Role not found.")
    else:
        member_role = Role.objects.filter(name="member", is_default=True).first()
        if member_role:
            user.roles.add(member_role)

    return 201, UserCreateOut(
        id=str(user.id),
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        temporary_password=temp_password,
    )


@router.get(
    "/users/",
    response={200: list[UserOut], 403: ErrorOut},
    auth=JWTAuth(),
)
def list_users(request):
    if not request.auth.has_permission(PermissionKey.MANAGE_USERS):
        return 403, ErrorOut(detail="Permission denied.")
    users = User.objects.prefetch_related("roles").order_by("email")
    return 200, [UserOut.from_user(u) for u in users]


@router.patch(
    "/users/{user_id}/",
    response={200: UserOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def update_user(request, user_id: str, payload: UserPatchIn):
    if not request.auth.has_permission(PermissionKey.MANAGE_USERS):
        return 403, ErrorOut(detail="Permission denied.")
    try:
        user = User.objects.prefetch_related("roles").get(pk=user_id)
    except User.DoesNotExist:
        return 404, ErrorOut(detail="User not found.")

    if payload.email is not None:
        if User.objects.exclude(pk=user_id).filter(email=payload.email).exists():
            return 400, ErrorOut(detail="A user with that email already exists.")
        user.email = payload.email
    if payload.first_name is not None:
        user.first_name = payload.first_name
    if payload.last_name is not None:
        user.last_name = payload.last_name
    if payload.is_active is not None:
        user.is_active = payload.is_active
    user.save()
    return 200, UserOut.from_user(user)


@router.delete(
    "/users/{user_id}/",
    response={204: None, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def delete_user(request, user_id: str):
    if not request.auth.has_permission(PermissionKey.MANAGE_USERS):
        return 403, ErrorOut(detail="Permission denied.")
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return 404, ErrorOut(detail="User not found.")
    if str(user.pk) == str(request.auth.pk):
        return 400, ErrorOut(detail="You cannot delete your own account.")
    if _is_last_admin(user):
        return 400, ErrorOut(detail="Cannot delete the last admin.")
    user.delete()
    return 204, None


@router.patch(
    "/users/{user_id}/roles/",
    response={200: UserOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def update_user_roles(request, user_id: str, payload: UserRolesIn):
    if not request.auth.has_permission(PermissionKey.MANAGE_USERS):
        return 403, ErrorOut(detail="Permission denied.")
    try:
        user = User.objects.prefetch_related("roles").get(pk=user_id)
    except User.DoesNotExist:
        return 404, ErrorOut(detail="User not found.")

    roles = list(Role.objects.filter(pk__in=payload.role_ids))
    if len(roles) != len(payload.role_ids):
        return 400, ErrorOut(detail="One or more role IDs not found.")

    admin_role = Role.objects.filter(name="admin", is_default=True).first()
    if admin_role:
        if str(user.pk) == str(request.auth.pk) and user.roles.filter(pk=admin_role.pk).exists():
            if admin_role not in roles:
                return 400, ErrorOut(detail="You cannot remove your own admin role.")
        if _is_last_admin(user) and admin_role not in roles:
            return 400, ErrorOut(detail="Cannot remove admin from the last admin.")

    user.roles.set(roles)
    user = User.objects.prefetch_related("roles").get(pk=user.pk)
    return 200, UserOut.from_user(user)


@router.post(
    "/users/{user_id}/reset-password/",
    response={200: ResetPasswordOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def reset_password(request, user_id: str):
    if not request.auth.has_permission(PermissionKey.MANAGE_USERS):
        return 403, ErrorOut(detail="Permission denied.")
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return 404, ErrorOut(detail="User not found.")
    temp_password = _generate_temp_password()
    user.set_password(temp_password)
    user.save()
    return 200, ResetPasswordOut(
        detail="Password reset. Share the temporary password with the user.",
        temporary_password=temp_password,
    )


# ---------------------------------------------------------------------------
# Role management endpoints
# ---------------------------------------------------------------------------


@router.get("/roles/", response={200: list[RoleOut]}, auth=JWTAuth())
def list_roles(request):
    roles = Role.objects.all()
    return 200, [
        RoleOut(id=str(r.id), name=r.name, is_default=r.is_default, permissions=r.permissions)
        for r in roles
    ]


@router.post(
    "/roles/",
    response={201: RoleOut, 400: ErrorOut, 403: ErrorOut},
    auth=JWTAuth(),
)
def create_role(request, payload: RoleIn):
    if not request.auth.has_permission(PermissionKey.MANAGE_ROLES):
        return 403, ErrorOut(detail="Permission denied.")
    if Role.objects.filter(name=payload.name).exists():
        return 400, ErrorOut(detail="A role with that name already exists.")
    role = Role.objects.create(name=payload.name, permissions=payload.permissions)
    return 201, RoleOut(id=str(role.id), name=role.name, is_default=role.is_default, permissions=role.permissions)


@router.patch(
    "/roles/{role_id}/",
    response={200: RoleOut, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def update_role(request, role_id: str, payload: RolePatchIn):
    if not request.auth.has_permission(PermissionKey.MANAGE_ROLES):
        return 403, ErrorOut(detail="Permission denied.")
    try:
        role = Role.objects.get(pk=role_id)
    except Role.DoesNotExist:
        return 404, ErrorOut(detail="Role not found.")

    if payload.name is not None and payload.name != role.name:
        if role.name in PROTECTED_ROLE_NAMES:
            return 400, ErrorOut(detail=f"Cannot rename protected role '{role.name}'.")
        if Role.objects.exclude(pk=role_id).filter(name=payload.name).exists():
            return 400, ErrorOut(detail="A role with that name already exists.")
        role.name = payload.name

    if payload.permissions is not None:
        role.permissions = payload.permissions

    role.save()
    return 200, RoleOut(id=str(role.id), name=role.name, is_default=role.is_default, permissions=role.permissions)


@router.delete(
    "/roles/{role_id}/",
    response={204: None, 400: ErrorOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def delete_role(request, role_id: str):
    if not request.auth.has_permission(PermissionKey.MANAGE_ROLES):
        return 403, ErrorOut(detail="Permission denied.")
    try:
        role = Role.objects.get(pk=role_id)
    except Role.DoesNotExist:
        return 404, ErrorOut(detail="Role not found.")
    if role.name in PROTECTED_ROLE_NAMES:
        return 400, ErrorOut(detail=f"Cannot delete protected role '{role.name}'.")
    if role.users.exists():
        return 400, ErrorOut(detail="Cannot delete a role that has users assigned.")
    role.delete()
    return 204, None
