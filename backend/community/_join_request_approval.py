import logging

from django.conf import settings
from django.utils import timezone
from notifications._email_helpers import send_join_approval_email
from notifications.email_sender import get_email_sender
from users._helpers import ConsentTimestamps, _create_magic_token
from users.api import _create_user_with_role
from users.models import NonMemberRsvpToken, User
from users.roles import Role

from community._shared import render_template_placeholders, validate_display_name
from community.models import (
    EventType,
    JoinRequestStatus,
    MemberPromotionEmailTemplate,
    WhatsAppLinkConfig,
)


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


def _grant_membership(user) -> None:
    """Add the default member role and revoke any scoped rsvp tokens."""
    member_role = Role.objects.filter(name="member", is_default=True).first()
    if member_role:
        user.roles.add(member_role)

    NonMemberRsvpToken.objects.filter(user=user, revoked_at__isnull=True).update(
        revoked_at=timezone.now()
    )


def _promote_public_non_member(user, join_request) -> str:
    """Promote a publicly-RSVP'd non-member to a member in place.

    Their prior RSVPs already point at this row, so flipping is_member keeps the
    full history instead of orphaning it under a fresh account.

    They have never onboarded — no password, and the scoped rsvp tokens that
    were their only way in are revoked here — so they are sent through
    onboarding and the magic token returned is what replaces those tokens.
    Dropping it would lock them out of the account they were just promoted into.
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
    _grant_membership(user)
    return _create_magic_token(user)


def _promote_tentative_member(user, join_request) -> None:
    """Promote a tentatively-approved applicant to a full member in place.

    They onboarded on first login, so they already have a password, a name they
    chose themselves, and cleared onboarding. Only membership changes here: no
    token to mint (they sign in normally), no onboarding to re-flag — doing so
    would lock them out, since the auth gate blocks every endpoint until it is
    cleared — and no name to overwrite with the one from their application.

    Their own first_name is still checked, so this path cannot produce a
    nameless member either (Issue 733).
    """
    validate_display_name(user.first_name, field="first_name")
    user.is_member = True
    if join_request.guidelines_consent_at is not None and user.guidelines_consent_at is None:
        user.guidelines_consent_at = join_request.guidelines_consent_at
    if join_request.sms_consent_at is not None and user.sms_consent_at is None:
        user.sms_consent_at = join_request.sms_consent_at
    user.save(update_fields=["is_member", "guidelines_consent_at", "sms_consent_at"])
    _grant_membership(user)


_DEFAULT_MEMBER_PROMOTION_EMAIL = "you now have full member access."


def send_join_approval(*, to: str, display_name: str, first_name: str) -> None:
    """Best-effort promotion email. A send failure must not roll back approval."""
    if not to:
        return
    template = MemberPromotionEmailTemplate.get()
    body = template.body.strip() or _DEFAULT_MEMBER_PROMOTION_EMAIL
    message_body = render_template_placeholders(
        body,
        {"FIRST_NAME": first_name, "WHATSAPP_LINK": WhatsAppLinkConfig.get().link},
    )
    try:
        send_join_approval_email(
            sender=get_email_sender(),
            to=to,
            display_name=display_name,
            message_body=message_body,
            login_url=f"{settings.FRONTEND_BASE_URL}/login",
        )
    except Exception:
        logging.getLogger(__name__).warning("join approval email failed", exc_info=True)


def _provision_tentative_user(join_request, requesting_user) -> tuple[User, str]:
    """Provision the non-member User backing a tentatively-approved join request.

    Reuses a non-member already linked or matched by phone; else creates one.
    They get the same way in as a fully-approved member — onboarding plus a
    magic token — but keep ``is_member=False`` and no member role, which is what
    limits them to official/club events (see ``community/_non_member_access``).
    Returns ``(user, magic_token)``.
    """
    user = join_request.user or User.objects.filter(phone_number=join_request.phone_number).first()
    if user is None:
        user = User.objects.create(
            phone_number=join_request.phone_number,
            first_name=join_request.first_name,
            last_name=join_request.last_name,
            email=join_request.email,
            is_member=False,
        )
        user.set_unusable_password()
        user.save(update_fields=["password"])

    if join_request.user_id != user.pk:
        join_request.user = user
        join_request.save(update_fields=["user"])

    # Carry the form's consents forward, same as _promote_non_member — they
    # consented when they applied, so the consent gate must not ask again.
    changed = ["needs_onboarding"] if not user.needs_onboarding else []
    user.needs_onboarding = True
    if join_request.guidelines_consent_at is not None and user.guidelines_consent_at is None:
        user.guidelines_consent_at = join_request.guidelines_consent_at
        changed.append("guidelines_consent_at")
    if join_request.sms_consent_at is not None and user.sms_consent_at is None:
        user.sms_consent_at = join_request.sms_consent_at
        changed.append("sms_consent_at")
    if changed:
        user.save(update_fields=changed)

    return user, _create_magic_token(user)


def _maybe_promote_tentative(user, event, actor) -> bool:
    """Promote a tentative applicant to full member when they check in.

    Fires only for an ATTENDED check-in on an official/club event whose RSVP'd
    user has a linked TENTATIVE join request. Returns whether a promotion
    happened, so the caller knows to send the approval email.
    """
    if event.event_type not in (EventType.OFFICIAL, EventType.CLUB):
        return False
    join_request = user.join_requests.filter(status=JoinRequestStatus.TENTATIVE).first()
    if join_request is None:
        return False

    _promote_tentative_member(user, join_request)
    join_request.status = JoinRequestStatus.APPROVED
    join_request.approved_at = timezone.now()
    join_request.approved_by = actor
    join_request.save(update_fields=["status", "approved_at", "approved_by"])
    return True


def _provision_approved_user(
    join_request, requesting_user, *, was_tentative: bool
) -> tuple[str | None, bool]:
    """Create, reactivate, or promote the user for an approved join request.

    Returns ``(magic_token, user_created)``: the one-time login token and whether
    a brand-new User row was created. A tentative applicant already has a login,
    so their promotion returns no token. When the phone already maps to an active
    member, nothing is provisioned and ``(None, False)`` is returned.
    """
    # A linked non-member is promoted in place; SET_NULL FK means a deleted user falls through.
    if join_request.user is not None and not join_request.user.is_member:
        if was_tentative:
            _promote_tentative_member(join_request.user, join_request)
            return None, False
        return _promote_public_non_member(join_request.user, join_request), False

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
