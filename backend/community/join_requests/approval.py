import logging

from django.conf import settings
from django.utils import timezone
from notifications.email_helpers import send_join_approval_email
from notifications.email_sender import get_email_sender
from users.api import create_user_with_role
from users.helpers import ConsentTimestamps, create_magic_token, grant_membership
from users.models import (
    MEMBER_OR_ARCHIVED,
    PAUSED_STATUSES,
    MembershipStatus,
    User,
    status_change_stamp,
)

from community.models import (
    JoinRequestStatus,
    MemberPromotionEmailTemplate,
    WhatsAppLinkConfig,
    is_official_or_club,
)
from community.shared import render_template_placeholders, validate_display_name


def _resolve_names(join_request) -> tuple[str, str]:
    """Return validated (first_name, last_name) for an approved join request.

    Raises REQUIRED when first_name is empty, so no approval path (create,
    promote, reactivate) can produce a member with an empty first_name (Issue 733).
    """
    validate_display_name(join_request.first_name, field="first_name")
    return join_request.first_name, join_request.last_name


def _unarchive(user, active_status: MembershipStatus, by: User) -> list[str]:
    """Clear the archive; a pause it was archived under comes back instead of active_status.

    return(list[str]): the fields it changed, for update_fields.
    """
    user.archived_at = None
    before = user.status_before_archive
    status = before if before in PAUSED_STATUSES else active_status
    if status == MembershipStatus.ATTENDANCE_PAUSED:
        user.attendance_paused_at = user.attendance_paused_at or timezone.now()
    else:
        user.attendance_paused_at = None
    user.status_before_archive = None
    fields = ["archived_at", "attendance_paused_at", "status_before_archive"]
    return [*fields, *user.set_membership_status(status, by=by)]


def _reactivate_archived_user(existing_user, join_request, by: User):
    """Un-archive an existing user on re-approval, carrying any new consents."""
    existing_user.needs_onboarding = True
    existing_user.first_name, existing_user.last_name = _resolve_names(join_request)
    if join_request.guidelines_consent_at is not None:
        existing_user.guidelines_consent_at = join_request.guidelines_consent_at
    if join_request.sms_consent_at is not None:
        existing_user.sms_consent_at = join_request.sms_consent_at
    existing_user.save(
        update_fields=[
            *_unarchive(existing_user, MembershipStatus.ACTIVE_MEMBER, by),
            "needs_onboarding",
            "first_name",
            "last_name",
            "guidelines_consent_at",
            "sms_consent_at",
        ]
    )
    if existing_user.membership_status == MembershipStatus.ACTIVE_MEMBER:
        # An archived applicant never had the member role.
        grant_membership(existing_user)
    return create_magic_token(existing_user)


def _promote_public_rsvper(user, join_request, by: User) -> str:
    """Promote a public rsvper in place; returns their replacement login token.

    param(user): the public rsvper User to promote, linked to join_request.
    return(str): magic token replacing the rsvp tokens this revokes.
    """
    user.is_member = True
    # Never onboarded and no password — dropping the token below strands them.
    user.needs_onboarding = True
    user.first_name, user.last_name = _resolve_names(join_request)
    if join_request.guidelines_consent_at is not None:
        user.guidelines_consent_at = join_request.guidelines_consent_at
    if join_request.sms_consent_at is not None:
        user.sms_consent_at = join_request.sms_consent_at
    user.save(
        update_fields=[
            "is_member",
            *user.set_membership_status(MembershipStatus.ACTIVE_MEMBER, by=by),
            "needs_onboarding",
            "first_name",
            "last_name",
            "guidelines_consent_at",
            "sms_consent_at",
        ]
    )
    grant_membership(user)
    return create_magic_token(user)


def promote_tentative_member(user, join_request, by: User) -> None:
    """Promote a tentatively-approved applicant in place; they onboarded already.

    Only membership changes: no token to mint, no needs_onboarding re-flag
    (that would lock them out of every endpoint), no name to overwrite.
    """
    # Their own name, not the application's — this path copies none (Issue 733).
    validate_display_name(user.first_name, field="first_name")
    user.is_member = True
    if join_request.guidelines_consent_at is not None and user.guidelines_consent_at is None:
        user.guidelines_consent_at = join_request.guidelines_consent_at
    if join_request.sms_consent_at is not None and user.sms_consent_at is None:
        user.sms_consent_at = join_request.sms_consent_at
    user.save(
        update_fields=[
            "is_member",
            *user.set_membership_status(MembershipStatus.ACTIVE_MEMBER, by=by),
            "guidelines_consent_at",
            "sms_consent_at",
        ]
    )
    grant_membership(user)


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


def _make_tentative(user, by: User) -> list[str]:
    """Move a non-member or archived account to tentative; return the changed fields."""
    if user.membership_status == MembershipStatus.NONE:
        return user.set_membership_status(MembershipStatus.TENTATIVE, by=by)
    if user.archived_at is None:
        return []
    fields = _unarchive(user, MembershipStatus.TENTATIVE, by)
    if user.membership_status == MembershipStatus.TENTATIVE:
        # Archiving keeps every role, and a non-member may hold none.
        user.roles.clear()
    return fields


def provision_tentative_user(join_request, requesting_user) -> tuple[User, str]:
    """Provision the non-member User backing a tentatively-approved join request.

    Reuses a non-member or archived account linked or matched by phone, un-archiving
    it; else creates one.
    They get the same way in as a fully-approved member — onboarding plus a
    magic token — but stay non-members with no member role, which is what
    limits them to official/club events (see ``community/events/limited_access``).
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
            membership_status=MembershipStatus.TENTATIVE,
            **status_change_stamp(requesting_user),
        )
        user.set_unusable_password()
        user.save(update_fields=["password"])

    if join_request.user_id != user.pk:
        join_request.user = user
        join_request.save(update_fields=["user"])

    # Carry the form's consents forward, same as _promote_non_member — they
    # consented when they applied, so the consent gate must not ask again.
    changed = ["needs_onboarding"] if not user.needs_onboarding else []
    changed += _make_tentative(user, requesting_user)
    user.needs_onboarding = True
    if join_request.guidelines_consent_at is not None and user.guidelines_consent_at is None:
        user.guidelines_consent_at = join_request.guidelines_consent_at
        changed.append("guidelines_consent_at")
    if join_request.sms_consent_at is not None and user.sms_consent_at is None:
        user.sms_consent_at = join_request.sms_consent_at
        changed.append("sms_consent_at")
    if changed:
        user.save(update_fields=changed)

    return user, create_magic_token(user)


def maybe_promote_tentative(user, event, actor) -> bool:
    """Promote a tentative applicant to full member when they check in.

    Fires only for an ATTENDED check-in on an official/club event whose RSVP'd
    user has a linked TENTATIVE join request. Returns whether a promotion
    happened, so the caller knows to send the approval email.
    """
    # An archived re-applicant can be tentative under a guidelines pause; check-in doesn't lift it.
    if not is_official_or_club(event.event_type) or user.is_guidelines_paused:
        return False
    join_request = user.join_requests.filter(status=JoinRequestStatus.TENTATIVE).first()
    if join_request is None:
        return False

    promote_tentative_member(user, join_request, actor)
    join_request.status = JoinRequestStatus.APPROVED
    join_request.approved_at = timezone.now()
    join_request.approved_by = actor
    join_request.status_changed_at = timezone.now()
    join_request.status_changed_by = actor
    join_request.approved_via_event = event
    join_request.save(
        update_fields=[
            "status",
            "approved_at",
            "approved_by",
            "status_changed_at",
            "status_changed_by",
            "approved_via_event",
        ]
    )
    return True


def provision_approved_user(
    join_request, requesting_user, *, was_tentative: bool
) -> tuple[str | None, bool]:
    """Create, reactivate, or promote the user for an approved join request.

    Returns ``(magic_token, user_created)``: the one-time login token and whether
    a brand-new User row was created. A tentative applicant already has a login,
    so their promotion returns no token. When the phone already maps to an active
    member, nothing is provisioned and ``(None, False)`` is returned.
    """
    # A linked non-member is promoted in place; an archived one is reactivated below.
    # SET_NULL FK means a deleted user falls through.
    linked = join_request.user
    if linked is not None and linked.membership_status not in MEMBER_OR_ARCHIVED:
        if was_tentative:
            promote_tentative_member(join_request.user, join_request, requesting_user)
            return None, False
        return _promote_public_rsvper(join_request.user, join_request, requesting_user), False

    existing_user = User.objects.filter(phone_number=join_request.phone_number).first()
    if existing_user is None:
        first_name, last_name = _resolve_names(join_request)
        _, magic_token = create_user_with_role(
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
        return _reactivate_archived_user(existing_user, join_request, requesting_user), True
    return None, False
