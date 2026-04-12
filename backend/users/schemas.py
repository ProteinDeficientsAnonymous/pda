from typing import Annotated

from community._field_limits import FieldLimit
from config.media_proxy import media_path
from pydantic import BaseModel, BeforeValidator, EmailStr, Field

from users.models import User


def _empty_str_to_none(v: str | None) -> str | None:
    if v is None or (isinstance(v, str) and v.strip() == ""):
        return None
    return v


OptionalEmail = Annotated[EmailStr | None, BeforeValidator(_empty_str_to_none)]


class LoginIn(BaseModel):
    phone_number: str = Field(max_length=FieldLimit.PHONE)
    password: str = Field(max_length=FieldLimit.PASSWORD)


class TokenOut(BaseModel):
    access: str
    refresh: str


class RefreshIn(BaseModel):
    refresh: str = Field(max_length=500)


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
    login_link_requested: bool = False
    week_start: str = "sunday"
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
            login_link_requested=user.login_link_requested,
            week_start=user.week_start,
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
    login_link_requested: bool = False


class UserCreateIn(BaseModel):
    phone_number: str = Field(max_length=FieldLimit.PHONE)
    display_name: str = Field(default="", max_length=FieldLimit.DISPLAY_NAME)
    email: OptionalEmail = None
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
    phone_number: str | None = Field(default=None, max_length=FieldLimit.PHONE)
    display_name: str | None = Field(default=None, max_length=FieldLimit.DISPLAY_NAME)
    email: OptionalEmail = None
    is_paused: bool | None = None


class MePatchIn(BaseModel):
    display_name: str | None = Field(default=None, max_length=FieldLimit.DISPLAY_NAME)
    email: OptionalEmail = None
    needs_onboarding: bool | None = None
    show_phone: bool | None = None
    show_email: bool | None = None
    week_start: str | None = None


class ChangePasswordIn(BaseModel):
    current_password: str = Field(max_length=FieldLimit.PASSWORD)
    new_password: str = Field(max_length=FieldLimit.PASSWORD)


class UserRolesIn(BaseModel):
    role_ids: list[str]


class ResetPasswordOut(BaseModel):
    detail: str
    magic_link_token: str


class RoleIn(BaseModel):
    name: str = Field(max_length=FieldLimit.ROLE_NAME)
    permissions: list[str] = []


class RolePatchIn(BaseModel):
    name: str | None = Field(default=None, max_length=FieldLimit.ROLE_NAME)
    permissions: list[str] | None = None


class ErrorOut(BaseModel):
    detail: str


class OnboardingIn(BaseModel):
    new_password: str = Field(max_length=FieldLimit.PASSWORD)
    display_name: str | None = Field(default=None, max_length=FieldLimit.DISPLAY_NAME)
    email: OptionalEmail = None


class UserSearchOut(BaseModel):
    id: str
    display_name: str
    phone_number: str
