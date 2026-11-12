import secrets
import uuid
from datetime import timedelta

import phonenumbers
from community.validation import Code, raise_validation
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, prefetch_related_objects
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver
from django.utils import timezone

from users.roles import Role  # noqa: F401 — re-exported so Django discovers it in the users app

# Fallback for bare digits only — a number with an explicit country code is unaffected.
ADMIN_ENTERED_PHONE_REGION = "US"
PUBLIC_FORM_PHONE_REGION = None

HAS_EMAIL = Q(email__isnull=False) & ~Q(email="")
STATUS_CHANGE_FIELDS = (
    "membership_status",
    "membership_status_changed_at",
    "membership_status_changed_by",
)


def status_change_stamp(by: "User | None") -> dict:
    """Create kwargs that record who set a new account's first status."""
    return {"membership_status_changed_at": timezone.now(), "membership_status_changed_by": by}


def can_sign_in_q() -> Q:
    """Members, plus tentative and attendance-paused non-members."""
    return Q(membership_status__in=SIGN_IN_STATUSES)


def limited_q() -> Q:
    """Signed-in non-members: tentatively approved or attendance-paused; never guidelines-paused."""
    return Q(membership_status__in=LIMITED_STATUSES)


def _parse_phone(raw: str, default_region: str | None) -> str | None:
    try:
        parsed = phonenumbers.parse(raw, default_region)
    except phonenumbers.phonenumberutil.NumberParseException:
        return None
    if not phonenumbers.is_valid_number(parsed):
        return None
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def validate_phone(raw: str, default_region: str | None, field: str = "phone_number") -> str:
    """Parse, validate, and return E.164. Raises ValidationException on invalid."""
    canonical = _parse_phone(raw, default_region)
    if canonical is None:
        raise_validation(Code.Phone.INVALID, field=field)
    return canonical


def normalize_phone_number(raw: str) -> str:
    """Best-effort canonicalize to E.164 for save() — never raises on bad legacy data."""
    return _parse_phone(raw, ADMIN_ENTERED_PHONE_REGION) or raw


class MembershipStatus(models.TextChoices):
    NONE = "none", "none"
    TENTATIVE = "tentative", "tentative"
    ACTIVE_MEMBER = "active_member", "active member"
    ATTENDANCE_PAUSED = "attendance_paused", "attendance paused"
    ARCHIVED = "archived", "archived"
    GUIDELINES_PAUSED = "guidelines_paused", "guidelines paused"


# Paused members keep the member role; only active members get full access.
MEMBER_STATUSES = (
    MembershipStatus.ACTIVE_MEMBER,
    MembershipStatus.GUIDELINES_PAUSED,
    MembershipStatus.ATTENDANCE_PAUSED,
)
LIMITED_STATUSES = (MembershipStatus.TENTATIVE, MembershipStatus.ATTENDANCE_PAUSED)
PAUSED_STATUSES = (MembershipStatus.GUIDELINES_PAUSED, MembershipStatus.ATTENDANCE_PAUSED)
# Members not limited to official/club events; a guidelines pause blocks login outright.
FULL_MEMBER_STATUSES = (MembershipStatus.ACTIVE_MEMBER, MembershipStatus.GUIDELINES_PAUSED)
SIGN_IN_STATUSES = (*MEMBER_STATUSES, MembershipStatus.TENTATIVE)
MEMBER_OR_ARCHIVED = (*MEMBER_STATUSES, MembershipStatus.ARCHIVED)
# The admin members screen lists tentative people too, so they can be archived.
MANAGED_STATUSES = (*MEMBER_OR_ARCHIVED, MembershipStatus.TENTATIVE)


class WeekStart:
    SUNDAY = "sunday"
    MONDAY = "monday"
    VALID = {SUNDAY, MONDAY}
    CHOICES = [(SUNDAY, "Sunday"), (MONDAY, "Monday")]


class CalendarFeedScope:
    ALL = "all"
    MINE = "mine"
    VALID = {ALL, MINE}
    CHOICES = [(ALL, "all events"), (MINE, "my events")]


class UserManager(BaseUserManager):
    def members(self):
        """Members only — excludes non-members created by public RSVP.

        Use on member-facing surfaces (directory, roles, recipient lists). The
        default manager returns both, for auth/login/join lookups by phone/email.
        """
        return self.get_queryset().filter(membership_status__in=MEMBER_STATUSES)

    def members_or_archived(self):
        """Members plus archived members: everyone admins manage as members."""
        return self.get_queryset().filter(membership_status__in=MEMBER_OR_ARCHIVED)

    def managed(self):
        """Everyone on the admin members screen: members, archived members and tentative people."""
        return self.get_queryset().filter(membership_status__in=MANAGED_STATUSES)

    def active_members(self):
        """Members for member-facing surfaces; the directory also drops onboarding-pending ones."""
        # is_active is only ever cleared from the Django admin; kept as defense in depth.
        return self.get_queryset().filter(
            membership_status=MembershipStatus.ACTIVE_MEMBER,
            is_active=True,
            archived_at__isnull=True,
        )

    def limited_users(self):
        """Users matching ``limited_q``."""
        return self.get_queryset().filter(limited_q())

    def active_limited_users(self):
        """Limited users, filtered like ``active_members``."""
        return self.limited_users().filter(is_active=True, archived_at__isnull=True)

    def with_permission(self, key: str):
        """Members granted `key` via role permissions, honoring the admin-default rule."""
        return self.members().filter(roles__id__in=Role.ids_with_permission(key)).distinct()

    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError("Phone number is required")
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_member", True)
        extra_fields.setdefault("membership_status", MembershipStatus.ACTIVE_MEMBER)
        return self.create_user(phone_number, password, **extra_fields)


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=64, blank=True, default="")
    last_name = models.CharField(max_length=64, blank=True, default="")
    # Defaults False; non-members are excluded via objects.members().
    is_member = models.BooleanField(default=False, db_index=True)
    membership_status = models.CharField(
        max_length=20,
        choices=MembershipStatus.choices,
        default=MembershipStatus.NONE,
        db_index=True,
    )
    membership_status_changed_at = models.DateTimeField(null=True, blank=True)
    membership_status_changed_by = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    # Uniqueness enforced by a partial constraint (see Meta) so multiple
    # members can share a null/blank email.
    email = models.EmailField(null=True, blank=True)
    roles = models.ManyToManyField(Role, blank=True, related_name="users")
    needs_onboarding = models.BooleanField(default=False)
    onboarded_at = models.DateTimeField(null=True, blank=True)
    needs_password_reset = models.BooleanField(default=False)
    guidelines_consent_at = models.DateTimeField(null=True, blank=True)
    sms_consent_at = models.DateTimeField(null=True, blank=True)
    contact_privacy_consent_at = models.DateTimeField(null=True, blank=True)
    calendar_token = models.CharField(max_length=64, blank=True, default="", db_index=True)
    bio = models.CharField(max_length=500, blank=True, default="")
    pronouns = models.CharField(max_length=100, blank=True, default="")
    nickname = models.CharField(max_length=64, blank=True, default="")
    birthday_month = models.PositiveSmallIntegerField(null=True, blank=True)
    birthday_day = models.PositiveSmallIntegerField(null=True, blank=True)
    birthday_year = models.PositiveSmallIntegerField(null=True, blank=True)
    veganniversary_month = models.PositiveSmallIntegerField(null=True, blank=True)
    veganniversary_day = models.PositiveSmallIntegerField(null=True, blank=True)
    veganniversary_year = models.PositiveSmallIntegerField(null=True, blank=True)
    show_veganniversary = models.BooleanField(default=True)
    veganniversary_shoutout_opt_in = models.BooleanField(default=True)
    has_seen_veganniversary = models.BooleanField(default=False)
    profile_photo = models.ImageField(upload_to="profile_photos/", blank=True)
    photo_updated_at = models.DateTimeField(null=True, blank=True)
    show_phone = models.BooleanField(default=True)
    show_email = models.BooleanField(default=True)
    show_birthday = models.BooleanField(default=True)
    hide_last_name = models.BooleanField(default=False)
    weekly_digest_opt_out = models.BooleanField(default=False)
    monthly_digest_opt_out = models.BooleanField(default=False)
    monthly_digest_sent_on = models.DateField(null=True, blank=True)
    whatsapp_reminder_opt_out = models.BooleanField(default=False)
    attendance_nudge_opt_out = models.BooleanField(default=False)
    host_digest_opt_out = models.BooleanField(default=False)
    host_digest_last_sent_at = models.DateTimeField(null=True, blank=True)
    is_paused = models.BooleanField(default=False)
    attendance_paused_at = models.DateTimeField(null=True, blank=True)
    restored_at = models.DateTimeField(null=True, blank=True)
    unpaused_at = models.DateTimeField(null=True, blank=True)
    attendance_grace_notified_at = models.DateTimeField(null=True, blank=True)
    has_joined_whatsapp = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True, db_index=True)
    status_before_archive = models.CharField(
        max_length=20, choices=MembershipStatus.choices, null=True, blank=True
    )
    login_link_requested = models.BooleanField(default=False)
    week_start = models.CharField(
        max_length=10, choices=WeekStart.CHOICES, default=WeekStart.SUNDAY
    )
    calendar_feed_scope = models.CharField(
        max_length=10,
        choices=CalendarFeedScope.CHOICES,
        default=CalendarFeedScope.ALL,
    )
    calendar_feed_excluded_types = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Remove inherited AbstractUser fields
    username = None

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = ["first_name"]
    objects = UserManager()

    class Meta:
        constraints = [
            # Unique email only when set — allows many users with null/blank email.
            models.UniqueConstraint(
                fields=["email"],
                condition=models.Q(email__isnull=False) & ~models.Q(email=""),
                name="unique_non_blank_email",
            ),
        ]

    def set_membership_status(self, status: MembershipStatus, *, by: "User | None") -> list[str]:
        """param(by): who made the change, or None for the system.
        return(list[str]): the fields it changed, for update_fields."""
        if self.archived_at is not None and status != MembershipStatus.ARCHIVED:
            # Archived stays archived; the change waits here until reactivation restores it.
            self.status_before_archive = status
            return ["status_before_archive"]
        if status != self.membership_status:
            self.membership_status = status
            self.membership_status_changed_at = timezone.now()
            self.membership_status_changed_by = by
        return list(STATUS_CHANGE_FIELDS)

    def apply_guidelines_pause(self, *, by: "User | None") -> list[str]:
        """A guidelines pause replaces any attendance pause."""
        self.attendance_paused_at = None
        self.unpaused_at = None
        status_fields = self.set_membership_status(MembershipStatus.GUIDELINES_PAUSED, by=by)
        return ["attendance_paused_at", "unpaused_at", *status_fields]

    def lift_guidelines_pause(self, *, by: "User | None") -> list[str]:
        # Lifting leaves them limited until a compliant in-person check-in.
        self.attendance_paused_at = timezone.now()
        self.has_joined_whatsapp = False
        status_fields = self.set_membership_status(MembershipStatus.ATTENDANCE_PAUSED, by=by)
        return ["attendance_paused_at", "has_joined_whatsapp", *status_fields]

    @property
    def is_guidelines_paused(self) -> bool:
        """True for an archived user archived while guidelines-paused too, so archiving can't shed it."""
        if self.membership_status == MembershipStatus.ARCHIVED:
            return self.status_before_archive == MembershipStatus.GUIDELINES_PAUSED
        return self.membership_status == MembershipStatus.GUIDELINES_PAUSED

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def needs_contact_privacy_consent(self) -> bool:
        # Already hiding something means they've seen the toggles; PATCH /me/ stamps consent on toggle.
        if not self.show_phone or not self.show_email:
            return False
        return self.contact_privacy_consent_at is None

    def save(self, *args, **kwargs):
        if self.phone_number:
            self.phone_number = normalize_phone_number(self.phone_number)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.full_name or self.phone_number

    def has_permission(self, key: str) -> bool:
        """Return True if any of the user's roles grants this permission key."""
        # Cached after the first call; roles.add/remove/set/clear invalidate it.
        if "roles" not in getattr(self, "_prefetched_objects_cache", {}):
            prefetch_related_objects([self], "roles")
        for role in self._prefetched_objects_cache["roles"]:
            # effective_permissions expands the admin role and guards corrupt rows
            if key in role.effective_permissions:
                return True
        return False


class MagicLoginTokenSource(models.TextChoices):
    # Only SELF_SERVICE counts toward the self-service login-link cooldown.
    SELF_SERVICE = "self_service", "Self-service"
    ADMIN = "admin", "Admin"
    REMINDER = "reminder", "Reminder"


class MagicLoginToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="magic_tokens")
    token = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    # LINK KIND: marks this token as a self-service "request a login link" token
    # (vs. an admin onboarding link). The consume endpoint is shared by both, so the
    # token carries which it is; consuming a token with this set flips the user's
    # persistent User.needs_password_reset. Admin onboarding links leave this False.
    requires_password_reset = models.BooleanField(default=False)
    source = models.CharField(
        max_length=20,
        choices=MagicLoginTokenSource.choices,
        default=MagicLoginTokenSource.ADMIN,
    )

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    @classmethod
    def create_for_user(
        cls,
        user: "User",
        *,
        requires_password_reset: bool = False,
        source: str = MagicLoginTokenSource.ADMIN,
    ) -> "MagicLoginToken":
        return cls.objects.create(
            user=user,
            expires_at=timezone.now() + timedelta(days=7),
            requires_password_reset=requires_password_reset,
            source=source,
        )


# Number of days a public rsvper's RSVP-management link stays valid from issuance.
PUBLIC_RSVP_TOKEN_TTL_DAYS = 90
# Absolute cap on a token's life, even with repeated extension, to bound leak exposure.
PUBLIC_RSVP_TOKEN_MAX_LIFETIME_DAYS = 180


class PublicRsvpToken(models.Model):
    """Scoped magic link for a public rsvper to manage their own RSVPs at /my-rsvps.

    This token NEVER logs the user in — it is entirely separate from
    MagicLoginToken (different table, different validation path, narrower scope).
    It grants scoped read/write to one non-member's RSVPs only. On a non-member's
    RSVP we EXTEND their existing valid token (see issue_or_extend) rather than
    minting a new one, so a link saved from a previous email keeps working; a
    fresh token is only issued when there is no valid one. Revoked when the user
    converts to a member.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="rsvp_tokens")
    token = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    # Distinct from expiry: a non-null revoked_at permanently kills the token
    # even before expires_at (set on member conversion or by an admin tool).
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"rsvp token for {self.user_id}"

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    @property
    def is_valid(self) -> bool:
        return not self.is_expired and not self.is_revoked

    def revoke(self) -> None:
        """Mark this token revoked. No-op if already revoked."""
        if self.revoked_at is None:
            self.revoked_at = timezone.now()
            self.save(update_fields=["revoked_at"])

    @classmethod
    def issue(cls, user: "User") -> "PublicRsvpToken":
        """Create a fresh token for a non-member, valid for 90 days.

        Rejects members — a converted/existing member must use the member flow,
        not the scoped non-member RSVP link.
        """
        if user.membership_status in FULL_MEMBER_STATUSES:
            raise ValidationError("Cannot issue a non-member RSVP token for a member.")
        return cls.objects.create(
            user=user,
            token=secrets.token_urlsafe(32),
            expires_at=timezone.now() + timedelta(days=PUBLIC_RSVP_TOKEN_TTL_DAYS),
        )

    @classmethod
    def issue_or_extend(cls, user: "User") -> "PublicRsvpToken":
        """Return a usable non-member RSVP token, reusing one when possible.

        Extends the newest valid token still within its absolute lifetime (so an
        emailed link keeps resolving), else issues a fresh one. Rejects members.
        """
        if user.membership_status in FULL_MEMBER_STATUSES:
            raise ValidationError("Cannot issue a non-member RSVP token for a member.")
        existing = user.rsvp_tokens.first()
        max_age_cutoff = timezone.now() - timedelta(days=PUBLIC_RSVP_TOKEN_MAX_LIFETIME_DAYS)
        if existing is not None and existing.is_valid and existing.created_at > max_age_cutoff:
            existing.expires_at = timezone.now() + timedelta(days=PUBLIC_RSVP_TOKEN_TTL_DAYS)
            existing.save(update_fields=["expires_at"])
            return existing
        return cls.issue(user)

    @classmethod
    def resolve_user(cls, token: str) -> "User | None":
        """Resolve a token string to its User, or None if the token is unusable.

        Returns None when the token is unknown, expired (expires_at < now),
        revoked (revoked_at set), or its user is guidelines-paused. Endpoints in
        stages 3/4 reuse this and map a None result to their own 404. Never logs
        the user in.
        """
        if not token:
            return None
        row = cls.objects.select_related("user").filter(token=token).first()
        if row is None or not row.is_valid or row.user.is_guidelines_paused:
            return None
        return row.user


@receiver(m2m_changed, sender=User.roles.through)
def reject_role_for_non_member(sender, instance, action, reverse, pk_set, **kwargs):
    """Reject any role assignment where the user is not a member.

    Fires on every role-assignment path (``user.roles.add``, ``role.users.add``,
    etc.). Callers should gate on membership first; reaching this guard means one
    didn't, so the ``ValueError`` surfaces as a loud 500 — fix the caller, don't
    catch it.

    ``reverse`` is part of Django's ``m2m_changed`` signature: it is ``True`` when
    the signal fires from the role side (``role.users.add``) and ``False`` from
    the user side (``user.roles.add``).
    """
    if action != "pre_add" or not pk_set:
        return
    signal_from_role_side = reverse
    if signal_from_role_side:
        if (
            User.objects.filter(pk__in=pk_set)
            .exclude(membership_status__in=MEMBER_OR_ARCHIVED)
            .exists()
        ):
            raise ValueError("cannot assign a role to a non-member user")
    elif instance.membership_status not in MEMBER_OR_ARCHIVED:
        raise ValueError("cannot assign a role to a non-member user")


@receiver(post_save, sender=User)
def assign_admin_role_to_superuser(sender, instance, created, **kwargs):
    """Automatically assign the admin role to any newly created superuser."""
    if created and instance.is_superuser:
        try:
            admin_role = Role.objects.get(name="admin", is_default=True)
            instance.roles.add(admin_role)
        except Role.DoesNotExist:
            pass
