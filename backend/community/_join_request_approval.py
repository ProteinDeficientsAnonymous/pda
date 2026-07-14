"""User provisioning for approved join requests (create / reactivate / promote)."""

import logging

from django.utils import timezone
from notifications._email_helpers import send_join_approval_email
from notifications.email_sender import get_email_sender
from users._helpers import ConsentTimestamps, _create_magic_token
from users.api import _create_user_with_role
from users.models import NonMemberRsvpToken, User
from users.roles import Role

from community._shared import render_template_placeholders, validate_display_name
from community.models import EventType, JoinRequestStatus, TentativeApprovalMessageTemplate


def _resolve_names(join_request) -> tuple[str, str]:
    """Return validated (first_name, last_name) for an approved join request.

    Raises REQUIRED when first_name is empty, so no approval path (create,
    promote, reactivate) can produce a member with an empty first_name (Issue 733).
    """
    validate_display_name(join_request.first_name, field="first_name")
    return join_request.first_name, join_request.last_name


def _reactivate_archived_user(existing_user, join_request):
    """Un-archive an existing user on re-approval, carrying any new consents."""
    existing_user.archived_at = None
    existing_user.needs_onboarding = True
    existing_user.first_name, existing_user.last_name = _resolve_names(join_request)
    if join_request.guidelines_consent_at is not None:
        existing_user.guidelines_consent_at = join_request.guidelines_consent_at
    if join_request.sms_consent_at is not None:
        existing_user.sms_consent_at = join_request.sms_consent_at
    existing_user.save(
        update_fields=[
            "archived_at",
            "needs_onboarding",
            "first_name",
            "last_name",
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
    user.first_name, user.last_name = _resolve_names(join_request)
    if join_request.guidelines_consent_at is not None:
        user.guidelines_consent_at = join_request.guidelines_consent_at
    if join_request.sms_consent_at is not None:
        user.sms_consent_at = join_request.sms_consent_at
    user.save(
        update_fields=[
            "is_member",
            "needs_onboarding",
            "first_name",
            "last_name",
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


_DEFAULT_TENTATIVE_APPROVAL_MESSAGE = (
    "you now have full member access. you'll receive a separate login link to set up your account."
)


def send_join_approval(*, to: str, display_name: str, first_name: str) -> None:
    """Best-effort full-approval email. A send failure must not roll back approval."""
    if not to:
        return
    template = TentativeApprovalMessageTemplate.get()
    body = template.body.strip() or _DEFAULT_TENTATIVE_APPROVAL_MESSAGE
    message_body = render_template_placeholders(body, {"FIRST_NAME": first_name})
    try:
        send_join_approval_email(
            sender=get_email_sender(),
            to=to,
            display_name=display_name,
            message_body=message_body,
        )
    except Exception:
        logging.getLogger(__name__).warning("join approval email failed", exc_info=True)


def _provision_tentative_user(join_request, requesting_user) -> User:
    """Provision the non-member User backing a tentatively-approved join request.

    Reuses a non-member already linked or matched by phone; else creates one. A
    scoped RSVP token is minted so they can RSVP without being a member. No member
    role, no login email — those wait for full approval.
    """
    user = join_request.user or User.objects.filter(phone_number=join_request.phone_number).first()
    if user is None:
        user = User.objects.create(
            phone_number=join_request.phone_number,
            first_name=join_request.first_name,
            last_name=join_request.last_name,
            email=join_request.email or None,
            is_member=False,
        )
        user.set_unusable_password()
        user.save(update_fields=["password"])

    if join_request.user_id != user.pk:
        join_request.user = user
        join_request.save(update_fields=["user"])

    NonMemberRsvpToken.issue_or_extend(user)
    return user


def _maybe_promote_tentative(user, event, actor) -> bool:
    """Promote a tentative applicant to full member when they check in.

    Fires only for an ATTENDED check-in on an official/club event whose RSVP'd
    user has a linked TENTATIVE join request. Returns whether a promotion ran so
    the caller can send the approval email. No-op otherwise.
    """
    if event.event_type not in (EventType.OFFICIAL, EventType.CLUB):
        return False
    join_request = user.join_requests.filter(status=JoinRequestStatus.TENTATIVE).first()
    if join_request is None:
        return False

    _promote_non_member(user, join_request)
    join_request.status = JoinRequestStatus.APPROVED
    join_request.approved_at = timezone.now()
    join_request.approved_by = actor
    join_request.save(update_fields=["status", "approved_at", "approved_by"])
    return True


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
        first_name, last_name = _resolve_names(join_request)
        _, magic_token = _create_user_with_role(
            join_request.phone_number,
            first_name,
            last_name,
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
