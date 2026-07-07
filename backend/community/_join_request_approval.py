"""User provisioning for approved join requests (create / reactivate + consent carry)."""

from users._helpers import ConsentTimestamps, _create_magic_token
from users.api import _create_user_with_role
from users.models import User


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


def _provision_approved_user(join_request, requesting_user):
    """Create or reactivate the user for an approved join request.

    Returns (magic_token, user_created). When the phone number already maps to an
    active user, nothing is provisioned and (None, False) is returned.
    """
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
