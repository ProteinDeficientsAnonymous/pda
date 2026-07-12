from datetime import datetime
from typing import Annotated, Literal

from community._field_limits import FieldLimit
from community._validation import Code, raise_validation
from config.media_proxy import media_path
from pydantic import BaseModel, BeforeValidator, EmailStr, Field, field_validator

from users._consents import ConsentType
from users.models import User
from users.permissions import PermissionKey


def _validate_permission_keys(permissions: list[str]) -> list[str]:
    """Reject any permission key not defined in PermissionKey.

    Roles persist permissions to a JSONField with no DB-level enforcement,
    so unknown/typo'd keys would silently become dead grants. Validate here.
    """
    valid = set(PermissionKey.values)
    for perm in permissions:
        if perm not in valid:
            raise_validation(
                Code.Role.INVALID_PERMISSION,
                field="permissions",
                permission=perm,
            )
    return permissions


def _empty_str_to_none(v: str | None) -> str | None:
    if v is None or (isinstance(v, str) and v.strip() == ""):
        return None
    return v


OptionalEmail = Annotated[EmailStr | None, BeforeValidator(_empty_str_to_none)]


class LoginIn(BaseModel):
    phone_number: str = Field(max_length=FieldLimit.PHONE)
    password: str = Field(max_length=FieldLimit.PASSWORD)


class TokenOut(BaseModel):
    # No `refresh` field — it rides the httpOnly cookie; in the body JS could steal it.
    access: str


class RefreshIn(BaseModel):
    # Optional because React clients send the refresh token via httpOnly cookie;
    # legacy Flutter clients still include it in the body.
    refresh: str = Field(default="", max_length=500)


class AccessOut(BaseModel):
    access: str


class LogoutOut(BaseModel):
    detail: str


class RoleOut(BaseModel):
    id: str
    name: str
    is_default: bool
    permissions: list[str]
    user_count: int = 0


class UserOut(BaseModel):
    id: str
    phone_number: str
    display_name: str
    first_name: str = ""
    last_name: str = ""
    full_name: str = ""
    nickname: str = ""
    email: str = ""
    bio: str = ""
    pronouns: str = ""
    is_superuser: bool = False
    needs_onboarding: bool = False
    needs_password_reset: bool = False
    needs_guidelines_consent: bool = False
    needs_sms_consent: bool = False
    profile_photo_url: str = ""
    photo_updated_at: str | None = None
    show_phone: bool = True
    show_email: bool = True
    hide_last_name: bool = False
    is_paused: bool = False
    login_link_requested: bool = False
    week_start: str = "sunday"
    calendar_feed_scope: str = "all"
    # Only populated by the list_users annotation; None everywhere else.
    last_attended: datetime | None = None
    roles: list[RoleOut]

    @classmethod
    def from_user(cls, user: User) -> "UserOut":
        return cls(
            id=str(user.id),
            phone_number=user.phone_number,
            display_name=user.display_name,
            first_name=user.first_name,
            last_name=user.last_name,
            full_name=user.full_name,
            nickname=user.nickname or "",
            email=user.email or "",
            bio=user.bio or "",
            pronouns=user.pronouns or "",
            is_superuser=user.is_superuser,
            needs_onboarding=user.needs_onboarding,
            needs_password_reset=user.needs_password_reset,
            needs_guidelines_consent=user.guidelines_consent_at is None,
            needs_sms_consent=user.sms_consent_at is None,
            profile_photo_url=media_path(user.profile_photo),
            photo_updated_at=(user.photo_updated_at.isoformat() if user.photo_updated_at else None),
            show_phone=user.show_phone,
            show_email=user.show_email,
            hide_last_name=user.hide_last_name,
            is_paused=user.is_paused,
            login_link_requested=user.login_link_requested,
            week_start=user.week_start,
            calendar_feed_scope=user.calendar_feed_scope,
            last_attended=getattr(user, "last_attended", None),
            roles=[
                RoleOut(
                    id=str(r.id),
                    name=r.name,
                    is_default=r.is_default,
                    permissions=r.effective_permissions,
                )
                for r in user.roles.all()
            ],
        )


class MemberProfileOut(BaseModel):
    id: str
    display_name: str
    first_name: str = ""
    last_name: str = ""
    full_name: str = ""
    nickname: str = ""
    phone_number: str
    email: str = ""
    bio: str = ""
    pronouns: str = ""
    profile_photo_url: str = ""
    login_link_requested: bool = False


class MemberDirectoryOut(BaseModel):
    id: str
    display_name: str
    first_name: str = ""
    last_name: str = ""
    full_name: str = ""
    phone_number: str = ""
    email: str = ""
    profile_photo_url: str = ""


class UserCreateIn(BaseModel):
    phone_number: str = Field(max_length=FieldLimit.PHONE)
    display_name: str = Field(default="", max_length=FieldLimit.DISPLAY_NAME)
    first_name: str = Field(default="", max_length=FieldLimit.FIRST_NAME)
    last_name: str = Field(default="", max_length=FieldLimit.LAST_NAME)
    email: OptionalEmail = None
    role_id: str | None = None


class UserCreateOut(BaseModel):
    id: str
    phone_number: str
    display_name: str
    first_name: str = ""
    last_name: str = ""
    full_name: str = ""
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
    first_name: str | None = Field(default=None, max_length=FieldLimit.FIRST_NAME)
    last_name: str | None = Field(default=None, max_length=FieldLimit.LAST_NAME)
    email: OptionalEmail = None
    is_paused: bool | None = None


class MePatchIn(BaseModel):
    display_name: str | None = Field(default=None, max_length=FieldLimit.DISPLAY_NAME)
    first_name: str | None = Field(default=None, max_length=FieldLimit.FIRST_NAME)
    last_name: str | None = Field(default=None, max_length=FieldLimit.LAST_NAME)
    email: OptionalEmail = None
    bio: str | None = Field(default=None, max_length=FieldLimit.BIO)
    pronouns: str | None = Field(default=None, max_length=FieldLimit.PRONOUNS)
    nickname: str | None = Field(default=None, max_length=FieldLimit.NICKNAME)
    needs_onboarding: bool | None = None
    show_phone: bool | None = None
    show_email: bool | None = None
    hide_last_name: bool | None = None
    week_start: Literal["sunday", "monday"] | None = None
    calendar_feed_scope: Literal["all", "mine"] | None = None


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

    @field_validator("permissions")
    @classmethod
    def validate_permissions(cls, v: list[str]) -> list[str]:
        return _validate_permission_keys(v)


class RolePatchIn(BaseModel):
    name: str | None = Field(default=None, max_length=FieldLimit.ROLE_NAME)
    permissions: list[str] | None = None

    @field_validator("permissions")
    @classmethod
    def validate_permissions(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        return _validate_permission_keys(v)


class ErrorOut(BaseModel):
    detail: str


class AcceptConsentsIn(BaseModel):
    consent_types: list[ConsentType] = Field(default_factory=list)


class OnboardingIn(BaseModel):
    new_password: str = Field(max_length=FieldLimit.PASSWORD)
    display_name: str | None = Field(default=None, max_length=FieldLimit.DISPLAY_NAME)
    first_name: str | None = Field(default=None, max_length=FieldLimit.FIRST_NAME)
    last_name: str | None = Field(default=None, max_length=FieldLimit.LAST_NAME)
    email: OptionalEmail = None
    pronouns: str | None = Field(default=None, max_length=FieldLimit.PRONOUNS)
    consent_types: list[ConsentType] = Field(default_factory=list)


class UserSearchOut(BaseModel):
    id: str
    display_name: str
    first_name: str = ""
    last_name: str = ""
    full_name: str = ""
    phone_number: str
