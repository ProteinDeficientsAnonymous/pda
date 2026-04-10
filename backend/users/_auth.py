"""Authentication endpoints (login, magic login, token refresh, me)."""

import logging

from community._shared import validate_display_name
from config.audit import audit_log
from config.media_proxy import media_path
from ninja import File, Router
from ninja.files import UploadedFile
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth
from ninja_jwt.tokens import RefreshToken

from users._password_validation import validate_password
from users.models import MagicLoginToken, User
from users.schemas import (
    AccessOut,
    ChangePasswordIn,
    ErrorOut,
    LoginIn,
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
def login(request, payload: LoginIn):
    from django.contrib.auth import authenticate

    auth_user = authenticate(request, username=payload.phone_number, password=payload.password)
    if auth_user is None:
        logger.warning("Authentication failure: invalid credentials")
        audit_log(
            logging.WARNING, "login_failed", request, details={"reason": "invalid_credentials"}
        )
        return Status(401, ErrorOut(detail="Invalid credentials"))
    user = User.objects.get(pk=auth_user.pk)
    if user.is_paused:
        audit_log(
            logging.WARNING, "login_paused", request, target_type="user", target_id=str(user.pk)
        )
        return Status(403, ErrorOut(detail="your membership is currently paused"))
    refresh = RefreshToken.for_user(user)
    request.auth = user
    audit_log(logging.INFO, "login_success", request, target_type="user", target_id=str(user.pk))
    return Status(200, TokenOut(access=str(refresh.access_token), refresh=str(refresh)))  # type: ignore


@router.get(
    "/magic-login/{token}/", response={200: TokenOut, 400: ErrorOut, 403: ErrorOut}, auth=None
)
def magic_login(request, token: str):
    try:
        magic = MagicLoginToken.objects.select_related("user").get(token=token)
    except MagicLoginToken.DoesNotExist:
        audit_log(
            logging.WARNING, "magic_login_failed", request, details={"reason": "invalid_token"}
        )
        return Status(400, ErrorOut(detail="Invalid or expired login link."))
    if magic.used or magic.is_expired:
        audit_log(
            logging.WARNING,
            "magic_login_failed",
            request,
            target_type="user",
            target_id=str(magic.user.pk),
            details={"reason": "used_or_expired"},
        )
        return Status(400, ErrorOut(detail="This login link has already been used or has expired."))
    if magic.user.is_paused:
        audit_log(
            logging.WARNING,
            "magic_login_paused",
            request,
            target_type="user",
            target_id=str(magic.user.pk),
        )
        return Status(403, ErrorOut(detail="your membership is currently paused"))
    magic.used = True
    magic.save(update_fields=["used"])
    refresh = RefreshToken.for_user(magic.user)
    request.auth = magic.user
    audit_log(
        logging.INFO,
        "magic_login_success",
        request,
        target_type="user",
        target_id=str(magic.user.pk),
    )
    return Status(200, TokenOut(access=str(refresh.access_token), refresh=str(refresh)))  # type: ignore


@router.post("/refresh/", response={200: AccessOut, 401: ErrorOut}, auth=None)
def refresh_token(request, payload: RefreshIn):
    from ninja_jwt.exceptions import TokenError

    try:
        refresh = RefreshToken(payload.refresh)
        return Status(200, AccessOut(access=str(refresh.access_token)))
    except TokenError:
        return Status(401, ErrorOut(detail="Invalid or expired refresh token"))
    except Exception:
        logger.exception("Unexpected error during token refresh")
        return Status(401, ErrorOut(detail="Token refresh failed"))


@router.get("/me/", response={200: UserOut, 401: ErrorOut, 403: ErrorOut}, auth=JWTAuth())
def me(request):
    user = User.objects.prefetch_related("roles").get(pk=request.auth.pk)
    if user.is_paused:
        return Status(403, ErrorOut(detail="your membership is currently paused"))
    return Status(200, UserOut.from_user(user))


@router.patch("/me/", response={200: UserOut, 400: ErrorOut}, auth=JWTAuth())
def update_me(request, payload: MePatchIn):
    user = User.objects.prefetch_related("roles").get(pk=request.auth.pk)
    changed = []
    if payload.display_name is not None:
        name_error = validate_display_name(payload.display_name)
        if name_error:
            return Status(400, ErrorOut(detail=name_error))
        user.display_name = payload.display_name.strip()
        changed.append("display_name")
    if payload.email is not None:
        user.email = payload.email
        changed.append("email")
    if payload.needs_onboarding is not None:
        user.needs_onboarding = payload.needs_onboarding
        changed.append("needs_onboarding")
    if payload.show_phone is not None:
        user.show_phone = payload.show_phone
        changed.append("show_phone")
    if payload.show_email is not None:
        user.show_email = payload.show_email
        changed.append("show_email")
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
        return Status(400, ErrorOut(detail="File must be a JPEG, PNG, WebP, or GIF image."))
    if photo.size and photo.size > _MAX_PHOTO_SIZE:
        return Status(400, ErrorOut(detail="Photo must be under 5 MB."))
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
    "/users/{user_id}/profile/",
    response={200: MemberProfileOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def get_member_profile(request, user_id: str):
    try:
        user = User.objects.get(pk=user_id, is_active=True, is_paused=False)
    except User.DoesNotExist:
        return Status(404, ErrorOut(detail="Member not found."))
    is_own_profile = str(request.auth.pk) == user_id
    return Status(
        200,
        MemberProfileOut(
            id=str(user.id),
            display_name=user.display_name,
            phone_number=user.phone_number if (user.show_phone or is_own_profile) else "",
            email=(user.email or "") if (user.show_email or is_own_profile) else "",
            profile_photo_url=media_path(user.profile_photo),
        ),
    )


@router.post("/complete-onboarding/", response={200: UserOut, 400: ErrorOut}, auth=JWTAuth())
def complete_onboarding(request, payload: OnboardingIn):
    pw_errors = validate_password(payload.new_password)
    if pw_errors:
        return Status(400, ErrorOut(detail="; ".join(pw_errors)))
    user = User.objects.prefetch_related("roles").get(pk=request.auth.pk)
    if payload.display_name is not None:
        name_error = validate_display_name(payload.display_name)
        if name_error:
            return Status(400, ErrorOut(detail=name_error))
        user.display_name = payload.display_name.strip()
    if payload.email:
        user.email = payload.email
    user.set_password(payload.new_password)
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
        return Status(400, ErrorOut(detail="Current password is incorrect."))
    pw_errors = validate_password(payload.new_password)
    if pw_errors:
        return Status(400, ErrorOut(detail="; ".join(pw_errors)))
    user.set_password(payload.new_password)
    user.save()
    audit_log(logging.INFO, "password_changed", request, target_type="user", target_id=str(user.pk))
    return Status(200, ErrorOut(detail="Password updated successfully."))
