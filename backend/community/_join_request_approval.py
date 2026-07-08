"""User provisioning for approved join requests (create / reactivate / promote)."""

from django.utils import timezone
from users._helpers import ConsentTimestamps, _create_magic_token
from users.api import _create_user_with_role
from users.models import NonMemberRsvpToken, User
from users.roles import Role


def _reactivate_archived_user(existing_user, join_request):
    """Un-archive an existing user on re-approval, carrying any new consents."""
    existing_user.archived_at = None
    existing_user.needs_onboarding = True
    existing_user.display_name = join_request.display_name
    if join_request.guidelines_consent_at is not None:
        existing_user.guidelines_consent_at = join_request.guidelines_consent_at
    if join_request.sms_consent_at is not None:
        existing_user.sms_consent_at = join_request.sms_consent_at
    existing_user.save(
        update_fields=[
            "archived_at",
            "needs_onboarding",
            "display_name",
            "guidelines_consent_at",
            "sms_consent_at",
        ]
    )
    return _create_magic_token(existing_user)


def _promote_non_member(user, join_request):
    """Promote a linked non-member User to a member in place.

    Their prior RSVPs already point at this row, so flipping is_member keeps the
    full history instead of orphaning it under a fresh account. Outstanding
    scoped RSVP tokens are revoked — the member flow replaces them.
    """
    user.is_member = True
    user.needs_onboarding = True
    user.display_name = join_request.display_name
    if join_request.guidelines_consent_at is not None:
        user.guidelines_consent_at = join_request.guidelines_consent_at
    if join_request.sms_consent_at is not None:
        user.sms_consent_at = join_request.sms_consent_at
    user.save(
        update_fields=[
            "is_member",
            "needs_onboarding",
            "display_name",
            "guidelines_consent_at",
            "sms_consent_at",
        ]
    )

    member_role = Role.objects.filter(name="member", is_default=True).first()
    if member_role:
        user.roles.add(member_role)

    NonMemberRsvpToken.objects.filter(user=user, revoked_at__isnull=True).update(
        revoked_at=timezone.now()
    )
    return _create_magic_token(user)


def _provision_approved_user(join_request, requesting_user) -> tuple[str | None, bool]:
    """Create, reactivate, or promote the user for an approved join request.

    Returns ``(magic_token, user_created)``: the one-time login token and whether
    a brand-new User row was created. A promoted non-member or reactivated
    archived user returns a token with ``user_created`` reflecting whether the
    row is new. When the phone already maps to an active member, nothing is
    provisioned and ``(None, False)`` is returned.
    """
    # A linked non-member is promoted in place; SET_NULL FK means a deleted user falls through.
    if join_request.user is not None and not join_request.user.is_member:
        return _promote_non_member(join_request.user, join_request), False

    existing_user = User.objects.filter(phone_number=join_request.phone_number).first()
    if existing_user is None:
        _, magic_token = _create_user_with_role(
            join_request.phone_number,
            join_request.display_name,
            join_request.email,
            None,
            requesting_user=requesting_user,
            consent=ConsentTimestamps(
                guidelines_consent_at=join_request.guidelines_consent_at,
                sms_consent_at=join_request.sms_consent_at,
            ),
        )
        return magic_token, True
    if existing_user.archived_at is not None:
        return _reactivate_archived_user(existing_user, join_request), True
    return None, False
