"""Authentication endpoints (login, magic login, token refresh, me)."""

import logging

from community._shared import validate_display_name
from community._validation import Code, raise_validation
from config.audit import audit_log
from config.media_proxy import media_path
from django.http import HttpResponse
from django.utils import timezone
from ninja import File, Router
from ninja.files import UploadedFile
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth
from ninja_jwt.tokens import RefreshToken

from users._password_validation import validate_password
from users._refresh_cookie import (
    clear_refresh_cookie,
    read_refresh_cookie,
    set_refresh_cookie,
)
from users.models import MagicLoginToken, User
from users.permissions import PermissionKey
from users.schemas import (
    AccessOut,
    ChangePasswordIn,
    ErrorOut,
    LoginIn,
    LogoutOut,
    MemberDirectoryOut,
    MemberProfileOut,
    MePatchIn,
    OnboardingIn,
    RefreshIn,
    TokenOut,
    UserOut,
)

logger = logging.getLogger("pda.auth")

router = Router()

_MAX_PHOTO_SIZE = 5 * 1024 * 1024  # 5 MB
_ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/heic",
    "image/heif",
}


@router.post("/login/", response={200: TokenOut, 401: ErrorOut, 403: ErrorOut}, auth=None)
def login(request, payload: LoginIn, response: HttpResponse):
    from django.contrib.auth import authenticate

    auth_user = authenticate(request, username=payload.phone_number, password=payload.password)
    if auth_user is None:
        logger.warning("Authentication failure: invalid credentials")
        audit_log(
            logging.WARNING, "login_failed", request, details={"reason": "invalid_credentials"}
        )
        raise_validation(Code.Auth.INVALID_CREDENTIALS, status_code=401)
    user = User.objects.get(pk=auth_user.pk)
    if user.archived_at is not None:
        audit_log(
            logging.WARNING, "login_archived", request, target_type="user", target_id=str(user.pk)
        )
        raise_validation(Code.Auth.ACCOUNT_ARCHIVED, status_code=403)
    if user.is_paused:
        audit_log(
            logging.WARNING, "login_paused", request, target_type="user", target_id=str(user.pk)
        )
        raise_validation(Code.Auth.ACCOUNT_PAUSED, status_code=403)
    refresh = RefreshToken.for_user(user)
    request.auth = user
    refresh_str = str(refresh)
    set_refresh_cookie(response, refresh_str)
    audit_log(logging.INFO, "login_success", request, target_type="user", target_id=str(user.pk))
    return Status(200, TokenOut(access=str(refresh.access_token), refresh=refresh_str))  # type: ignore


def _current_jwt_user(request) -> User | None:
    """Best-effort JWT read for endpoints declared with auth=None.

    Returns the authenticated user if the request carries a valid access token,
    else None. Any auth error (missing/invalid/expired token) is treated as
    anonymous — the calling endpoint decides whether that matters.
    """
    try:
        user = JWTAuth()(request)
    except Exception:
        return None
    if isinstance(user, User):
        return user
    return None


@router.get(
    "/magic-login/{token}/", response={200: TokenOut, 400: ErrorOut, 403: ErrorOut}, auth=None
)
def magic_login(request, token: str, response: HttpResponse):
    try:
        magic = MagicLoginToken.objects.select_related("user").get(token=token)
    except MagicLoginToken.DoesNotExist:
        audit_log(
            logging.WARNING, "magic_login_failed", request, details={"reason": "invalid_token"}
        )
        raise_validation(Code.Auth.MAGIC_LINK_INVALID_OR_EXPIRED, status_code=400)
    # Reject cross-user magic links: if the caller is already authenticated as a
    # different user, a silent session swap would let them complete onboarding /
    # password-set on behalf of the link's target. Force explicit logout first.
    current_user = _current_jwt_user(request)
    if current_user is not None and current_user.pk != magic.user.pk:
        audit_log(
            logging.WARNING,
            "magic_login_cross_user_blocked",
            request,
            target_type="user",
            target_id=str(magic.user.pk),
            details={"current_user_id": str(current_user.pk)},
        )
        raise_validation(Code.Auth.ALREADY_SIGNED_IN_AS_DIFFERENT_USER, status_code=403)
    if magic.used or magic.is_expired:
        audit_log(
            logging.WARNING,
            "magic_login_failed",
            request,
            target_type="user",
            target_id=str(magic.user.pk),
            details={"reason": "used_or_expired"},
        )
        raise_validation(Code.Auth.MAGIC_LINK_ALREADY_USED, status_code=400)
    if magic.user.archived_at is not None:
        audit_log(
            logging.WARNING,
            "magic_login_archived",
            request,
            target_type="user",
            target_id=str(magic.user.pk),
        )
        raise_validation(Code.Auth.ACCOUNT_ARCHIVED, status_code=403)
    if magic.user.is_paused:
        audit_log(
            logging.WARNING,
            "magic_login_paused",
            request,
            target_type="user",
            target_id=str(magic.user.pk),
        )
        raise_validation(Code.Auth.ACCOUNT_PAUSED, status_code=403)
    magic.used = True
    magic.save(update_fields=["used"])
    refresh = RefreshToken.for_user(magic.user)
    request.auth = magic.user
    refresh_str = str(refresh)
    set_refresh_cookie(response, refresh_str)
    audit_log(
        logging.INFO,
        "magic_login_success",
        request,
        target_type="user",
        target_id=str(magic.user.pk),
    )
    return Status(200, TokenOut(access=str(refresh.access_token), refresh=refresh_str))  # type: ignore


@router.post("/refresh/", response={200: AccessOut, 401: ErrorOut}, auth=None)
def refresh_token(request, payload: RefreshIn, response: HttpResponse):
    from ninja_jwt.exceptions import TokenError

    # Prefer httpOnly cookie (React). Fall back to body for Flutter clients
    # that still send the refresh token in the JSON payload.
    token = read_refresh_cookie(request) or payload.refresh
    if not token:
        raise_validation(Code.Auth.REFRESH_TOKEN_INVALID, status_code=401)
    try:
        refresh = RefreshToken(token)
        return Status(200, AccessOut(access=str(refresh.access_token)))
    except TokenError:
        raise_validation(
            Code.Auth.REFRESH_TOKEN_INVALID, status_code=401, clear_refresh_cookie=True
        )
    except Exception:
        logger.exception("Unexpected error during token refresh")
        raise_validation(Code.Auth.REFRESH_FAILED, status_code=401, clear_refresh_cookie=True)


@router.post("/logout/", response={200: LogoutOut}, auth=None)
def logout(request, response: HttpResponse):
    """Clear the refresh cookie. Idempotent; safe to call unauthenticated."""
    clear_refresh_cookie(response)
    return Status(200, LogoutOut(detail="logged out"))


@router.get("/me/", response={200: UserOut, 401: ErrorOut, 403: ErrorOut}, auth=JWTAuth())
def me(request):
    user = User.objects.prefetch_related("roles").get(pk=request.auth.pk)
    if user.is_paused:
        raise_validation(Code.Auth.ACCOUNT_PAUSED, status_code=403)
    return Status(200, UserOut.from_user(user))


def _apply_me_patch(user, payload: MePatchIn) -> list[str]:
    """Apply MePatchIn fields to user. Returns the list of changed fields.

    Raises ValidationException on invalid input — caller lets it propagate
    to the global handler.
    """
    changed: list[str] = []
    if payload.display_name is not None:
        validate_display_name(payload.display_name)
        user.display_name = payload.display_name.strip()
        changed.append("display_name")
    if payload.email is not None:
        user.email = payload.email
        changed.append("email")
    if payload.bio is not None:
        user.bio = payload.bio.strip()
        changed.append("bio")
    if payload.needs_onboarding is not None:
        user.needs_onboarding = payload.needs_onboarding
        changed.append("needs_onboarding")
    if payload.show_phone is not None:
        user.show_phone = payload.show_phone
        changed.append("show_phone")
    if payload.show_email is not None:
        user.show_email = payload.show_email
        changed.append("show_email")
    if payload.week_start is not None:
        user.week_start = payload.week_start
        changed.append("week_start")
    if payload.calendar_feed_scope is not None:
        user.calendar_feed_scope = payload.calendar_feed_scope
        changed.append("calendar_feed_scope")
    return changed


@router.patch("/me/", response={200: UserOut, 400: ErrorOut}, auth=JWTAuth())
def update_me(request, payload: MePatchIn):
    user = User.objects.prefetch_related("roles").get(pk=request.auth.pk)
    changed = _apply_me_patch(user, payload)
    user.save()
    if changed:
        audit_log(
            logging.INFO,
            "profile_updated",
            request,
            target_type="user",
            target_id=str(user.pk),
            details={"fields_changed": changed},
        )
    return Status(200, UserOut.from_user(user))


@router.post("/me/photo/", response={200: UserOut, 400: ErrorOut}, auth=JWTAuth())
def upload_photo(request, photo: UploadedFile = File(...)):  # ty: ignore[call-non-callable]
    if photo.content_type not in _ALLOWED_IMAGE_TYPES:
        raise_validation(
            Code.Photo.TYPE_NOT_ALLOWED,
            field="photo",
            status_code=400,
            allowed=sorted(_ALLOWED_IMAGE_TYPES),
        )
    if photo.size and photo.size > _MAX_PHOTO_SIZE:
        raise_validation(
            Code.Photo.TOO_LARGE,
            field="photo",
            status_code=400,
            max_mb=_MAX_PHOTO_SIZE // (1024 * 1024),
        )
    user = User.objects.prefetch_related("roles").get(pk=request.auth.pk)
    if user.profile_photo:
        user.profile_photo.delete(save=False)
    name = photo.name or ""
    ext = name.rsplit(".", 1)[-1] if "." in name else "jpg"
    user.profile_photo.save(f"{user.pk}.{ext}", photo, save=True)
    audit_log(
        logging.INFO, "profile_photo_uploaded", request, target_type="user", target_id=str(user.pk)
    )
    return Status(200, UserOut.from_user(user))


@router.delete("/me/photo/", response={200: UserOut}, auth=JWTAuth())
def delete_photo(request):
    user = User.objects.prefetch_related("roles").get(pk=request.auth.pk)
    if user.profile_photo:
        user.profile_photo.delete(save=False)
        user.profile_photo = ""
        user.save(update_fields=["profile_photo"])
    audit_log(
        logging.INFO, "profile_photo_deleted", request, target_type="user", target_id=str(user.pk)
    )
    return Status(200, UserOut.from_user(user))


@router.get(
    "/users/directory/",
    response={200: list[MemberDirectoryOut]},
    auth=JWTAuth(),
)
def list_member_directory(request):
    """Authed-only member directory. Respects each user's show_phone/show_email flags."""
    users = User.objects.filter(
        is_active=True,
        is_paused=False,
        archived_at__isnull=True,
        needs_onboarding=False,
    ).order_by("display_name", "phone_number")
    return Status(
        200,
        [
            MemberDirectoryOut(
                id=str(u.id),
                display_name=u.display_name or u.phone_number,
                phone_number=u.phone_number if u.show_phone else "",
                email=(u.email or "") if u.show_email else "",
                profile_photo_url=media_path(u.profile_photo),
            )
            for u in users
        ],
    )


@router.get(
    "/users/{user_id}/profile/",
    response={200: MemberProfileOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def get_member_profile(request, user_id: str):
    try:
        user = User.objects.get(
            pk=user_id, is_active=True, is_paused=False, archived_at__isnull=True
        )
    except User.DoesNotExist:
        raise_validation(Code.Member.NOT_FOUND, status_code=404)
    is_own_profile = str(request.auth.pk) == user_id
    can_manage_users = request.auth.has_permission(PermissionKey.MANAGE_USERS)
    return Status(
        200,
        MemberProfileOut(
            id=str(user.id),
            display_name=user.display_name,
            phone_number=user.phone_number if (user.show_phone or is_own_profile) else "",
            email=(user.email or "") if (user.show_email or is_own_profile) else "",
            bio=user.bio or "",
            profile_photo_url=media_path(user.profile_photo),
            login_link_requested=user.login_link_requested if can_manage_users else False,
        ),
    )


@router.post("/complete-onboarding/", response={200: UserOut, 400: ErrorOut}, auth=JWTAuth())
def complete_onboarding(request, payload: OnboardingIn):
    pw_errors = validate_password(payload.new_password)
    if pw_errors:
        raise_validation(
            Code.Password.INVALID, field="new_password", status_code=400, reasons=pw_errors
        )
    user = User.objects.prefetch_related("roles").get(pk=request.auth.pk)
    if payload.display_name is not None:
        validate_display_name(payload.display_name)
        user.display_name = payload.display_name.strip()
    if payload.email:
        user.email = payload.email
    user.set_password(payload.new_password)
    if user.needs_onboarding and user.onboarded_at is None:
        user.onboarded_at = timezone.now()
    user.needs_onboarding = False
    user.save()
    audit_log(
        logging.INFO, "onboarding_completed", request, target_type="user", target_id=str(user.pk)
    )
    return Status(200, UserOut.from_user(user))


@router.post("/change-password/", response={200: ErrorOut, 400: ErrorOut}, auth=JWTAuth())
def change_password(request, payload: ChangePasswordIn):
    user = User.objects.get(pk=request.auth.pk)
    if not user.check_password(payload.current_password):
        audit_log(
            logging.WARNING,
            "password_change_failed",
            request,
            target_type="user",
            target_id=str(user.pk),
            details={"reason": "wrong_current_password"},
        )
        raise_validation(
            Code.Auth.CURRENT_PASSWORD_INCORRECT, field="current_password", status_code=400
        )
    pw_errors = validate_password(payload.new_password)
    if pw_errors:
        raise_validation(
            Code.Password.INVALID, field="new_password", status_code=400, reasons=pw_errors
        )
    user.set_password(payload.new_password)
    user.save()
    audit_log(logging.INFO, "password_changed", request, target_type="user", target_id=str(user.pk))
    return Status(200, ErrorOut(detail="Password updated successfully."))
