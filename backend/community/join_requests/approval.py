import logging
from typing import NamedTuple

from config.audit import AuditTarget, AuditTargetType, actor_request, audit_log
from django.conf import settings
from django.utils import timezone
from notifications.email_helpers import send_join_approval_email
from notifications.email_sender import get_email_sender
from users.api import create_user_with_role
from users.helpers import (
    ConsentTimestamps,
    NewMemberFields,
    create_magic_token,
    grant_membership,
    revoke_public_rsvp_tokens,
)
from users.models import (
    MEMBER_OR_ARCHIVED,
    MembershipEvent,
    MembershipStatus,
    User,
    status_change_stamp,
)

from community.models import (
    JoinRequest,
    JoinRequestStatus,
    MemberPromotionEmailTemplate,
    WhatsAppLinkConfig,
    is_official_or_club,
)
from community.shared import render_template_placeholders, validate_display_name


def applicant_user(join_request) -> User | None:
    # The linked User may have been matched by email, so its phone can differ from the request's.
    return join_request.user or User.objects.filter(phone_number=join_request.phone_number).first()


def _resolve_names(join_request) -> tuple[str, str]:
    """Return validated (first_name, last_name) for an approved join request.

    Raises REQUIRED when first_name is empty, so no approval path (create,
    promote, reactivate) can produce a member with an empty first_name (Issue 733).
    """
    validate_display_name(join_request.first_name, field="first_name")
    return join_request.first_name, join_request.last_name


def _audit_user_membership(
    user: User, actor, action: str, event: MembershipEvent, extra: dict
) -> None:
    audit_log(
        logging.INFO,
        action,
        actor_request(None, actor),
        target=AuditTarget(
            type=AuditTargetType.USER,
            id=str(user.pk),
            details={"event": event, "to": str(user.membership_status), **extra},
        ),
    )


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
            *existing_user.approve_membership(by=by),
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
    _audit_user_membership(
        existing_user,
        by,
        "user_approved",
        MembershipEvent.APPROVE,
        {"from": MembershipStatus.ARCHIVED, "join_request_id": str(join_request.id)},
    )
    return create_magic_token(existing_user)


def _promote_public_rsvper(user, join_request, by: User) -> str:
    """Promote a public rsvper in place; returns their replacement login token.

    param(user): the public rsvper User to promote, linked to join_request.
    return(str): magic token replacing the rsvp tokens this revokes.
    """
    before = str(user.membership_status)
    # Never onboarded and no password — dropping the token below strands them.
    user.needs_onboarding = True
    user.first_name, user.last_name = _resolve_names(join_request)
    if join_request.guidelines_consent_at is not None:
        user.guidelines_consent_at = join_request.guidelines_consent_at
    if join_request.sms_consent_at is not None:
        user.sms_consent_at = join_request.sms_consent_at
    user.save(
        update_fields=[
            *user.approve_membership(by=by),
            "needs_onboarding",
            "first_name",
            "last_name",
            "guidelines_consent_at",
            "sms_consent_at",
        ]
    )
    grant_membership(user)
    _audit_user_membership(
        user,
        by,
        "user_approved",
        MembershipEvent.APPROVE,
        {"from": before, "join_request_id": str(join_request.id)},
    )
    return create_magic_token(user)


def promote_tentative_member(user, join_request, by: User) -> None:
    """Promote a tentatively-approved applicant in place; they onboarded already.

    Only membership changes: no token to mint, no needs_onboarding re-flag
    (that would lock them out of every endpoint), and their name stays theirs.
    """
    consents = _apply_tentative_consents(user, join_request)
    user.save(update_fields=[*user.approve_membership(by=by), *consents])
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


def _make_tentative(user, join_request, by: User) -> list[str]:
    """Move a non-member or archived account to tentative under the join form's name.

    return(list[str]): the fields it changed, for update_fields.
    """
    if user.is_archived:
        fields = user.mark_tentative(by=by)
        if user.membership_status == MembershipStatus.TENTATIVE:
            # Archiving keeps every role, and a non-member may hold none.
            user.roles.clear()
    elif user.membership_status == MembershipStatus.NONE:
        fields = user.mark_tentative(by=by)
    else:
        return []
    user.first_name, user.last_name = _resolve_names(join_request)
    return [*fields, "first_name", "last_name"]


def _apply_tentative_consents(user: User, join_request) -> list[str]:
    changed: list[str] = []
    if join_request.guidelines_consent_at is not None and user.guidelines_consent_at is None:
        user.guidelines_consent_at = join_request.guidelines_consent_at
        changed.append("guidelines_consent_at")
    if join_request.sms_consent_at is not None and user.sms_consent_at is None:
        user.sms_consent_at = join_request.sms_consent_at
        changed.append("sms_consent_at")
    return changed


def provision_tentative_user(join_request, requesting_user) -> tuple[User, str, bool]:
    """Provision the non-member User backing a tentatively-approved join request.

    Reuses a non-member or archived account linked or matched by phone, un-archiving
    it; else creates one.
    They get the same way in as a fully-approved member — onboarding plus a
    magic token — but stay non-members with no member role, which is what
    limits them to official/club events (see ``community/events/limited_access``).
    Returns ``(user, magic_token, reactivated)``; reactivated is True when it un-archived them.
    """
    user = applicant_user(join_request)
    before_status: str | None = None
    if user is None:
        user = User.objects.create(
            phone_number=join_request.phone_number,
            first_name=join_request.first_name,
            last_name=join_request.last_name,
            email=join_request.email,
            membership_status=MembershipStatus.TENTATIVE,
            **status_change_stamp(requesting_user),
        )
        user.set_unusable_password()
        user.save(update_fields=["password"])
        transitioned = True
    else:
        before_status = (
            MembershipStatus.ARCHIVED if user.is_archived else str(user.membership_status)
        )
        transitioned = user.is_archived or user.membership_status == MembershipStatus.NONE

    if join_request.user_id != user.pk:
        join_request.user = user
        join_request.save(update_fields=["user"])

    changed = ["needs_onboarding"] if not user.needs_onboarding else []
    was_archived = user.archived_at is not None
    changed += _make_tentative(user, join_request, requesting_user)
    user.needs_onboarding = True
    changed += _apply_tentative_consents(user, join_request)
    if changed:
        user.save(update_fields=changed)
    revoke_public_rsvp_tokens(user)
    if transitioned:
        _audit_user_membership(
            user,
            requesting_user,
            "user_marked_tentative",
            MembershipEvent.MARK_TENTATIVE,
            {"from": before_status, "join_request_id": str(join_request.id)},
        )

    return user, create_magic_token(user), was_archived and user.archived_at is None


def maybe_promote_tentative(user, event, actor) -> JoinRequest | None:
    """Promote a tentative applicant to full member on an ATTENDED official/club check-in.

    return(JoinRequest | None): the promoted join request, or None when nothing was promoted.
    """
    # An archived re-applicant can be tentative under a guidelines pause; check-in doesn't lift it.
    if (
        not is_official_or_club(event.event_type)
        or user.is_guidelines_paused
        or user.is_archived
        or user.membership_status != MembershipStatus.TENTATIVE
    ):
        return None
    join_request = user.join_requests.filter(status=JoinRequestStatus.TENTATIVE).first()
    if join_request is None:
        return None

    # Row lock: concurrent check-ins then re-check tentative before promoting.
    locked = User.objects.select_for_update().get(pk=user.pk)
    if locked.membership_status != MembershipStatus.TENTATIVE:
        return False
    user.refresh_from_db()
    consents = _apply_tentative_consents(user, join_request)
    user.save(update_fields=[*user.promote_on_check_in(by=actor), *consents])
    grant_membership(user)
    join_request.status = JoinRequestStatus.APPROVED
    join_request.status_changed_at = timezone.now()
    join_request.status_changed_by = actor
    join_request.approved_via_event = event
    join_request.save(
        update_fields=["status", "status_changed_at", "status_changed_by", "approved_via_event"]
    )
    _audit_user_membership(
        user,
        actor,
        "user_promoted_on_check_in",
        MembershipEvent.PROMOTE_ON_CHECK_IN,
        {
            "from": MembershipStatus.TENTATIVE,
            "event_id": str(event.pk),
            "join_request_id": str(join_request.id),
        },
    )
    return join_request


class Provisioned(NamedTuple):
    magic_token: str | None
    user_created: bool
    reactivated_user: User | None = None


def provision_approved_user(join_request, requesting_user, *, was_tentative: bool) -> Provisioned:
    """Create, reactivate, or promote the user for an approved join request.

    return(Provisioned): login token (None for a tentative promotion or an existing
    active member), user_created (also True on reactivation), and the reactivated user.
    """
    # A linked non-member is promoted in place; an archived one is reactivated below.
    # SET_NULL FK means a deleted user falls through.
    linked = join_request.user
    if linked is not None and linked.membership_status not in MEMBER_OR_ARCHIVED:
        if was_tentative:
            before = str(linked.membership_status)
            promote_tentative_member(linked, join_request, requesting_user)
            _audit_user_membership(
                linked,
                requesting_user,
                "user_approved",
                MembershipEvent.APPROVE,
                {"from": before, "join_request_id": str(join_request.id)},
            )
            return Provisioned(None, False)
        return Provisioned(
            _promote_public_rsvper(linked, join_request, requesting_user), False
        )

    existing_user = User.objects.filter(phone_number=join_request.phone_number).first()
    if existing_user is None:
        first_name, last_name = _resolve_names(join_request)
        created_user, magic_token = create_user_with_role(
            NewMemberFields(
                phone=join_request.phone_number,
                first_name=first_name,
                last_name=last_name,
                email=join_request.email,
            ),
            requesting_user=requesting_user,
            consent=ConsentTimestamps(
                guidelines_consent_at=join_request.guidelines_consent_at,
                sms_consent_at=join_request.sms_consent_at,
            ),
        )
        _audit_user_membership(
            created_user,
            requesting_user,
            "user_approved",
            MembershipEvent.APPROVE,
            {"from": None, "join_request_id": str(join_request.id)},
        )
        return Provisioned(magic_token, True)
    if existing_user.archived_at is not None:
        return Provisioned(
            _reactivate_archived_user(existing_user, join_request, requesting_user),
            True,
            existing_user,
        )
    return Provisioned(None, False)
