import secrets
import uuid
from datetime import timedelta

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver
from django.utils import timezone

from users._name_parsing import sync_display_name
from users.roles import Role  # noqa: F401 — re-exported so Django discovers it in the users app


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
        return self.get_queryset().filter(is_member=True)

    def active_members(self):
        """Members who should appear on member-facing surfaces.

        Bundles the full visibility predicate so call sites can't forget part of
        it (a bare ``members()`` would still leak paused/archived users). Use this
        for member-facing directory, profile, and search lookups.

        ``needs_onboarding`` is deliberately NOT filtered here — it's only excluded
        by the directory, which adds ``needs_onboarding=False`` itself. The profile
        and search surfaces intentionally include onboarding-pending members.

        On ``is_active``: this is Django's built-in ``AbstractUser`` flag, which the
        app never sets to False (``is_paused`` is the product's live suspension flag,
        enforced at the auth gate). It's kept here as cheap defense-in-depth guarding
        the only path that can deactivate a user — the Django admin.
        """
        return self.members().filter(
            is_active=True,
            is_paused=False,
            archived_at__isnull=True,
        )

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
        return self.create_user(phone_number, password, **extra_fields)


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField(max_length=20, unique=True)
    display_name = models.CharField(max_length=64, blank=True)
    first_name = models.CharField(max_length=64, blank=True, default="")
    last_name = models.CharField(max_length=64, blank=True, default="")
    # Defaults False; non-members are excluded via objects.members().
    is_member = models.BooleanField(default=False, db_index=True)
    # Uniqueness enforced by a partial constraint (see Meta) so multiple
    # members can share a null/blank email.
    email = models.EmailField(null=True, blank=True)
    roles = models.ManyToManyField(Role, blank=True, related_name="users")
    needs_onboarding = models.BooleanField(default=False)
    onboarded_at = models.DateTimeField(null=True, blank=True)
    needs_password_reset = models.BooleanField(default=False)
    guidelines_consent_at = models.DateTimeField(null=True, blank=True)
    sms_consent_at = models.DateTimeField(null=True, blank=True)
    calendar_token = models.CharField(max_length=64, blank=True, default="", db_index=True)
    bio = models.CharField(max_length=500, blank=True, default="")
    pronouns = models.CharField(max_length=100, blank=True, default="")
    nickname = models.CharField(max_length=64, blank=True, default="")
    birthday = models.DateField(null=True, blank=True)
    profile_photo = models.ImageField(upload_to="profile_photos/", blank=True)
    photo_updated_at = models.DateTimeField(null=True, blank=True)
    show_phone = models.BooleanField(default=True)
    show_email = models.BooleanField(default=True)
    hide_last_name = models.BooleanField(default=False)
    is_paused = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True, db_index=True)
    login_link_requested = models.BooleanField(default=False)
    week_start = models.CharField(
        max_length=10, choices=WeekStart.CHOICES, default=WeekStart.SUNDAY
    )
    calendar_feed_scope = models.CharField(
        max_length=10,
        choices=CalendarFeedScope.CHOICES,
        default=CalendarFeedScope.ALL,
    )
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

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def save(self, *args, **kwargs):
        sync_display_name(self, kwargs)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.full_name or self.phone_number

    def has_permission(self, key: str) -> bool:
        """Return True if any of the user's roles grants this permission key.

        Uses the prefetch cache when available (avoids N+1 in list views),
        otherwise falls back to a queryset.
        """
        cache = getattr(self, "_prefetched_objects_cache", {})
        roles = cache["roles"] if "roles" in cache else self.roles.all()
        for role in roles:
            # effective_permissions expands the admin role and guards corrupt rows
            if key in role.effective_permissions:
                return True
        return False


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

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    @classmethod
    def create_for_user(
        cls, user: "User", *, requires_password_reset: bool = False
    ) -> "MagicLoginToken":
        return cls.objects.create(
            user=user,
            expires_at=timezone.now() + timedelta(days=7),
            requires_password_reset=requires_password_reset,
        )


# Number of days a non-member RSVP-management link stays valid from issuance.
NON_MEMBER_RSVP_TOKEN_TTL_DAYS = 90
# Absolute cap on a token's life, even with repeated extension, to bound leak exposure.
NON_MEMBER_RSVP_TOKEN_MAX_LIFETIME_DAYS = 180


class NonMemberRsvpToken(models.Model):
    """Scoped magic link for a non-member to manage their own RSVPs at /my-rsvps.

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
    def issue(cls, user: "User") -> "NonMemberRsvpToken":
        """Create a fresh token for a non-member, valid for 90 days.

        Rejects members — a converted/existing member must use the member flow,
        not the scoped non-member RSVP link.
        """
        if user.is_member:
            raise ValidationError("Cannot issue a non-member RSVP token for a member.")
        return cls.objects.create(
            user=user,
            token=secrets.token_urlsafe(32),
            expires_at=timezone.now() + timedelta(days=NON_MEMBER_RSVP_TOKEN_TTL_DAYS),
        )

    @classmethod
    def issue_or_extend(cls, user: "User") -> "NonMemberRsvpToken":
        """Return a usable non-member RSVP token, reusing one when possible.

        Extends the newest valid token still within its absolute lifetime (so an
        emailed link keeps resolving), else issues a fresh one. Rejects members.
        """
        if user.is_member:
            raise ValidationError("Cannot issue a non-member RSVP token for a member.")
        existing = user.rsvp_tokens.first()
        max_age_cutoff = timezone.now() - timedelta(days=NON_MEMBER_RSVP_TOKEN_MAX_LIFETIME_DAYS)
        if existing is not None and existing.is_valid and existing.created_at > max_age_cutoff:
            existing.expires_at = timezone.now() + timedelta(days=NON_MEMBER_RSVP_TOKEN_TTL_DAYS)
            existing.save(update_fields=["expires_at"])
            return existing
        return cls.issue(user)

    @classmethod
    def resolve_user(cls, token: str) -> "User | None":
        """Resolve a token string to its User, or None if the token is unusable.

        Returns None when the token is unknown, expired (expires_at < now), or
        revoked (revoked_at set). Endpoints in stages 3/4 reuse this and map a
        None result to their own 404. Never logs the user in.
        """
        if not token:
            return None
        row = cls.objects.select_related("user").filter(token=token).first()
        if row is None or not row.is_valid:
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
        if User.objects.filter(pk__in=pk_set, is_member=False).exists():
            raise ValueError("cannot assign a role to a non-member user")
    elif not instance.is_member:
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
