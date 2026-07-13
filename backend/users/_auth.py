"""Authentication endpoints (login, magic login, token refresh, me)."""

import logging

from community._validation import Code, raise_validation
from config.audit import audit_log
from config.auth import gated_jwt
from config.ratelimit import client_ip, rate_limit
from django.contrib.auth import authenticate
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from ninja import File, Router
from ninja.files import UploadedFile
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth
from ninja_jwt.exceptions import TokenError
from ninja_jwt.tokens import RefreshToken

from users._consents import stamp_consents
from users._helpers import (
    _check_and_set_email,
    _resolve_name_fields,
)
from users._password_validation import validate_password
from users._refresh_cookie import (
    clear_refresh_cookie,
    read_refresh_cookie,
    set_refresh_cookie,
)
from users.models import MagicLoginToken, User
from users.schemas import (
    AcceptConsentsIn,
    AccessOut,
    ChangePasswordIn,
    ErrorOut,
    LoginIn,
    LogoutOut,
    MePatchIn,
    OnboardingIn,
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


@router.post(
    "/login/", response={200: TokenOut, 401: ErrorOut, 403: ErrorOut, 429: ErrorOut}, auth=None
)
@rate_limit(key_func=client_ip, rate="5/m")
def login(request, payload: LoginIn, response: HttpResponse):
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
    set_refresh_cookie(response, str(refresh))
    audit_log(logging.INFO, "login_success", request, target_type="user", target_id=str(user.pk))
    return Status(200, TokenOut(access=str(refresh.access_token)))  # type: ignore


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


def _validate_magic_user(request, magic: MagicLoginToken) -> None:
    """Run the non-consuming guards for a magic token. Raises on failure."""
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


def _consume_magic_token(request, token: str) -> MagicLoginToken:
    """Atomically fetch, validate, and mark a magic token used.

    Row-locked (select_for_update) so two concurrent requests can't both pass
    the used-check and replay the link (TOCTOU). Raises on any guard failure.
    """
    with transaction.atomic():
        try:
            magic = (
                MagicLoginToken.objects.select_for_update().select_related("user").get(token=token)
            )
        except MagicLoginToken.DoesNotExist:
            audit_log(
                logging.WARNING, "magic_login_failed", request, details={"reason": "invalid_token"}
            )
            raise_validation(Code.Auth.MAGIC_LINK_INVALID_OR_EXPIRED, status_code=400)
        _validate_magic_user(request, magic)
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
        magic.used = True
        magic.save(update_fields=["used"])
        if magic.requires_password_reset:
            # Self-service login link: the user got in without a password, so force a
            # reset before normal use. set_unusable_password() ensures the old password
            # can't be used until they pick a new one (cleared by complete_onboarding).
            # Also clear login_link_requested so future link requests aren't skipped.
            magic.user.needs_password_reset = True
            magic.user.login_link_requested = False
            magic.user.set_unusable_password()
            magic.user.save(
                update_fields=["needs_password_reset", "login_link_requested", "password"]
            )
            audit_log(
                logging.INFO,
                "magic_login_requires_password_reset",
                request,
                target_type="user",
                target_id=str(magic.user.pk),
            )
    return magic


@router.get(
    "/magic-login/{token}/",
    response={200: TokenOut, 400: ErrorOut, 403: ErrorOut, 429: ErrorOut},
    auth=None,
)
@rate_limit(key_func=client_ip, rate="5/m")
def magic_login(request, token: str, response: HttpResponse):
    magic = _consume_magic_token(request, token)
    refresh = RefreshToken.for_user(magic.user)
    request.auth = magic.user
    set_refresh_cookie(response, str(refresh))
    audit_log(
        logging.INFO,
        "magic_login_success",
        request,
        target_type="user",
        target_id=str(magic.user.pk),
    )
    return Status(200, TokenOut(access=str(refresh.access_token)))  # type: ignore


@router.post("/refresh/", response={200: AccessOut, 401: ErrorOut}, auth=None)
def refresh_token(request, response: HttpResponse):
    token = read_refresh_cookie(request)
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


@router.get("/me/", response={200: UserOut, 401: ErrorOut, 403: ErrorOut}, auth=gated_jwt)
def me(request):
    user = User.objects.prefetch_related("roles").get(pk=request.auth.pk)
    if user.is_paused:
        raise_validation(Code.Auth.ACCOUNT_PAUSED, status_code=403)
    return Status(200, UserOut.from_user(user))


# Fields copied straight from payload to user with no extra validation.
_ME_PATCH_PASSTHROUGH_FIELDS = (
    "needs_onboarding",
    "show_phone",
    "show_email",
    "hide_last_name",
    "week_start",
    "calendar_feed_scope",
)
# Passthrough fields that also get whitespace-stripped.
_ME_PATCH_STRIPPED_FIELDS = ("bio", "pronouns", "nickname")


def _apply_me_patch(user, payload: MePatchIn) -> list[str]:
    """Apply MePatchIn fields to user. Returns the list of changed fields.

    Raises ValidationException on invalid input — caller lets it propagate
    to the global handler.
    """
    changed: list[str] = []
    if _resolve_name_fields(user, payload):
        changed.extend(["first_name", "last_name", "display_name"])
    if payload.email is not None:
        _check_and_set_email(user, payload.email, exclude_pk=user.pk)
        changed.append("email")
    for attr in _ME_PATCH_STRIPPED_FIELDS:
        value = getattr(payload, attr)
        if value is not None:
            setattr(user, attr, value.strip())
            changed.append(attr)
    for attr in _ME_PATCH_PASSTHROUGH_FIELDS:
        value = getattr(payload, attr)
        if value is not None:
            setattr(user, attr, value)
            changed.append(attr)
    return changed


@router.patch("/me/", response={200: UserOut, 400: ErrorOut, 409: ErrorOut}, auth=gated_jwt)
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


@router.post("/me/photo/", response={200: UserOut, 400: ErrorOut}, auth=gated_jwt)
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
    user.profile_photo.save(f"{user.pk}.{ext}", photo, save=False)
    user.photo_updated_at = timezone.now()
    user.save(update_fields=["profile_photo", "photo_updated_at"])
    audit_log(
        logging.INFO, "profile_photo_uploaded", request, target_type="user", target_id=str(user.pk)
    )
    return Status(200, UserOut.from_user(user))


@router.delete("/me/photo/", response={200: UserOut}, auth=gated_jwt)
def delete_photo(request):
    user = User.objects.prefetch_related("roles").get(pk=request.auth.pk)
    if user.profile_photo:
        user.profile_photo.delete(save=False)
        user.profile_photo = ""
        user.photo_updated_at = None
        user.save(update_fields=["profile_photo", "photo_updated_at"])
    audit_log(
        logging.INFO, "profile_photo_deleted", request, target_type="user", target_id=str(user.pk)
    )
    return Status(200, UserOut.from_user(user))


@router.post(
    "/complete-onboarding/",
    response={200: UserOut, 400: ErrorOut, 409: ErrorOut, 422: ErrorOut},
    auth=gated_jwt,
)
def complete_onboarding(request, payload: OnboardingIn):
    pw_errors = validate_password(payload.new_password)
    if pw_errors:
        raise_validation(
            Code.Password.INVALID, field="new_password", status_code=400, reasons=pw_errors
        )
    user = User.objects.prefetch_related("roles").get(pk=request.auth.pk)
    # Reject reusing the current password. Only meaningful when the user still
    # has a usable one — a forced-reset user has an unusable password, so
    # check_password always fails and this is correctly skipped.
    if user.has_usable_password() and user.check_password(payload.new_password):
        raise_validation(Code.Password.SAME_AS_OLD, field="new_password", status_code=400)
    _resolve_name_fields(user, payload)
    if payload.email is not None:
        _check_and_set_email(user, payload.email, exclude_pk=user.pk)
    elif not user.email:
        raise_validation(Code.Email.REQUIRED, field="email", status_code=422)
    if payload.pronouns is not None:
        user.pronouns = payload.pronouns.strip()
    user.set_password(payload.new_password)
    if user.needs_onboarding and user.onboarded_at is None:
        user.onboarded_at = timezone.now()
    user.needs_onboarding = False
    user.needs_password_reset = False
    stamp_consents(user, payload.consent_types)
    user.save()
    audit_log(
        logging.INFO, "onboarding_completed", request, target_type="user", target_id=str(user.pk)
    )
    return Status(200, UserOut.from_user(user))


@router.post("/accept-consents/", response={200: UserOut}, auth=gated_jwt)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="10/m")
def accept_consents(request, payload: AcceptConsentsIn):
    """Record the consents the caller is accepting, clearing the relevant gates."""
    user = User.objects.prefetch_related("roles").get(pk=request.auth.pk)
    changed = stamp_consents(user, payload.consent_types)
    if changed:
        user.save(update_fields=changed)
    audit_log(
        logging.INFO,
        "consents_accepted",
        request,
        target_type="user",
        target_id=str(user.pk),
        details={"consent_types": [str(c) for c in payload.consent_types]},
    )
    return Status(200, UserOut.from_user(user))


@router.post("/change-password/", response={200: ErrorOut, 400: ErrorOut}, auth=gated_jwt)
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
    # current_password was just verified correct, so a matching new password is a
    # no-op reuse — reject it.
    if user.check_password(payload.new_password):
        raise_validation(Code.Password.SAME_AS_OLD, field="new_password", status_code=400)
    user.set_password(payload.new_password)
    # Setting a password also satisfies a pending forced reset.
    user.needs_password_reset = False
    user.save()
    audit_log(logging.INFO, "password_changed", request, target_type="user", target_id=str(user.pk))
    return Status(200, ErrorOut(detail="Password updated successfully."))
