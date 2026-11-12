"""Shared authentication for protected API endpoints.

``GatedJWTAuth`` is the single chokepoint that enforces *per-request* account
state on top of the JWT signature/expiry/``is_active`` checks the ninja-jwt
library already does. It exists because a valid access token outlives the state
changes that should revoke access:

  - ``set_unusable_password()`` only blocks the ``/login/`` form (which runs
    ``check_password``). It has no effect on a token that was already issued, so
    a self-service magic-login user could otherwise call any endpoint without
    ever setting a password.
  - a guidelines pause / ``archived_at`` were historically checked only at login and
    on ``/me/``, so a user paused *after* getting a token kept access until it
    expired. Enforcing here closes that hole too.

A pending user (needs password reset / onboarding) must still reach the few
endpoints required to *resolve* that state, so those paths are allowlisted.
"""

from collections.abc import Callable

from community.models import JoinRequest
from community.validation import Code, ValidationException
from django.http import HttpRequest
from ninja_jwt.authentication import JWTAuth
from users.models import SIGN_IN_STATUSES, MembershipStatus, User

# Full request paths (under the ``/api`` mount) a pending user may still reach:
#   - GET /me/                 — frontend reads needs_password_reset/onboarding/
#                                guidelines-consent state here
#   - POST /complete-onboarding/ — the only way to set a password / clear the flags
#   - POST /change-password/   — alternate password-set path (also clears the flag)
#   - POST /accept-consents/   — the only way to clear needs_guidelines_consent
# /refresh/ and /logout/ are auth=None, so they bypass this gate already.
_PENDING_ALLOWLIST = frozenset(
    {
        "/api/auth/me/",
        "/api/auth/complete-onboarding/",
        "/api/auth/change-password/",
        "/api/auth/accept-consents/",
    }
)

# Archive, guidelines pause and no membership still 403 on the pending allowlist; password and consent do not.
HARD_ACCOUNT_BLOCKS = frozenset(
    {
        Code.Auth.ACCOUNT_ARCHIVED,
        Code.Auth.ACCOUNT_GUIDELINES_PAUSED,
        Code.Auth.ACCOUNT_REJECTED,
        Code.Auth.NOT_A_MEMBER,
    }
)


_ACCOUNT_BLOCKS: tuple[tuple[Callable[[User], bool], str], ...] = (
    (lambda u: u.archived_at is not None, Code.Auth.ACCOUNT_ARCHIVED),
    (
        lambda u: u.membership_status == MembershipStatus.GUIDELINES_PAUSED,
        Code.Auth.ACCOUNT_GUIDELINES_PAUSED,
    ),
    (lambda u: u.membership_status not in SIGN_IN_STATUSES, Code.Auth.NOT_A_MEMBER),
    (lambda u: u.needs_password_reset, Code.Auth.PASSWORD_RESET_REQUIRED),
    (lambda u: u.needs_onboarding, Code.Auth.ONBOARDING_REQUIRED),
    (lambda u: u.guidelines_consent_at is None, Code.Auth.GUIDELINES_CONSENT_REQUIRED),
)


def _first_block_code(user: User) -> str | None:
    return next((code for blocks, code in _ACCOUNT_BLOCKS if blocks(user)), None)


def account_may_act(user: User) -> bool:
    """Whether the account is unblocked; safe in async code since it runs no query."""
    return _first_block_code(user) is None


def account_block_code(user: User) -> str | None:
    """Return the auth code that blocks this account, or None if it may act."""
    code = _first_block_code(user)
    # A rejected applicant is told they may request to join again.
    if code == Code.Auth.NOT_A_MEMBER and JoinRequest.latest_is_rejected(user.phone_number):
        return Code.Auth.ACCOUNT_REJECTED
    return code


class GatedJWTAuth(JWTAuth):
    """JWTAuth that also rejects tokens whose account is in a blocked state.

    Runs after the standard JWT validation. Raises ``ValidationException`` (the
    project's structured-error type, reshaped by the global exception handler)
    rather than returning None, so the client gets a specific code instead of a
    bare 401.
    """

    def authenticate(self, request: HttpRequest, token: str):
        user = super().authenticate(request, token)
        if not isinstance(user, User):
            return user

        code = account_block_code(user)
        if code is None or (request.path in _PENDING_ALLOWLIST and code not in HARD_ACCOUNT_BLOCKS):
            return user
        raise ValidationException(code, status_code=403)


# Single shared instance — import and pass as ``auth=gated_jwt`` everywhere a
# protected endpoint previously used ``auth=JWTAuth()``.
gated_jwt = GatedJWTAuth()
