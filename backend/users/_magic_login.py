"""Magic-login consumption: validate and redeem a magic token for a session."""

import logging

from community._validation import Code, raise_validation
from config.audit import audit_log
from config.ratelimit import client_ip, rate_limit
from django.db import transaction
from django.http import HttpResponse
from ninja import Router
from ninja.responses import Status
from ninja_jwt.authentication import JWTAuth
from ninja_jwt.tokens import RefreshToken

from users._refresh_cookie import set_refresh_cookie
from users.models import MagicLoginToken, User
from users.schemas import ErrorOut, TokenOut

router = Router()


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
