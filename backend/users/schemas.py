from config.media_proxy import media_path
from pydantic import BaseModel

from users.models import User


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
    profile_photo_url: str = ""
    show_phone: bool = True
    show_email: bool = True
    is_paused: bool = False
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
            profile_photo_url=media_path(user.profile_photo),
            show_phone=user.show_phone,
            show_email=user.show_email,
            is_paused=user.is_paused,
            roles=[
                RoleOut(
                    id=str(r.id), name=r.name, is_default=r.is_default, permissions=r.permissions
                )
                for r in user.roles.all()
            ],
        )


class MemberProfileOut(BaseModel):
    id: str
    display_name: str
    phone_number: str
    email: str = ""
    profile_photo_url: str = ""


class UserCreateIn(BaseModel):
    phone_number: str
    display_name: str = ""
    email: str = ""
    role_id: str | None = None


class UserCreateOut(BaseModel):
    id: str
    phone_number: str
    display_name: str
    magic_link_token: str


class BulkUserCreateIn(BaseModel):
    phone_numbers: list[str]


class BulkUserResult(BaseModel):
    row: int
    phone_number: str
    success: bool
    error: str | None = None
    magic_link_token: str | None = None


class BulkUserCreateOut(BaseModel):
    results: list[BulkUserResult]
    created: int
    failed: int


class UserPatchIn(BaseModel):
    phone_number: str | None = None
    display_name: str | None = None
    email: str | None = None
    is_paused: bool | None = None


class MePatchIn(BaseModel):
    display_name: str | None = None
    email: str | None = None
    needs_onboarding: bool | None = None
    show_phone: bool | None = None
    show_email: bool | None = None


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str


class UserRolesIn(BaseModel):
    role_ids: list[str]


class ResetPasswordOut(BaseModel):
    detail: str
    magic_link_token: str


class RoleIn(BaseModel):
    name: str
    permissions: list[str] = []


class RolePatchIn(BaseModel):
    name: str | None = None
    permissions: list[str] | None = None


class ErrorOut(BaseModel):
    detail: str


class OnboardingIn(BaseModel):
    new_password: str
    display_name: str | None = None
    email: str = ""


class UserSearchOut(BaseModel):
    id: str
    display_name: str
    phone_number: str
