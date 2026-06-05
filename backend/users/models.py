import uuid
from datetime import timedelta

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

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
        return self.create_user(phone_number, password, **extra_fields)


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField(max_length=20, unique=True)
    display_name = models.CharField(max_length=64, blank=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    roles = models.ManyToManyField(Role, blank=True, related_name="users")
    needs_onboarding = models.BooleanField(default=False)
    onboarded_at = models.DateTimeField(null=True, blank=True)
    # PERSISTENT USER STATE: "this person still owes us a new password." Set on
    # consume of a self-service login link (see MagicLoginToken.requires_password_reset),
    # read by the frontend from /me/ on every load to force a /new-password redirect,
    # and cleared by complete_onboarding. Distinct from needs_onboarding (first-time
    # name+password setup), which routes to /onboarding instead.
    needs_password_reset = models.BooleanField(default=False)
    # PERSISTENT USER STATE: when this user last accepted the community guidelines
    # and agreements. Null means they have never consented (or are being asked to
    # re-consent) — surfaced on /me/ as needs_guidelines_consent and enforced as a
    # hard gate (see config.auth.GatedJWTAuth). Stamped by POST /accept-guidelines/.
    # Deliberately NOT backfilled: everyone, admins included, must re-consent.
    guidelines_consent_at = models.DateTimeField(null=True, blank=True)
    # PERSISTENT USER STATE: when this user last accepted the SMS messaging
    # policy. Null means they have never consented. Mirrors guidelines_consent_at
    # and is surfaced on /me/ as needs_sms_consent, but — unlike guidelines — is
    # NOT a hard gate (see config.auth.GatedJWTAuth): we record SMS consent, we
    # do not lock legacy users out for lacking it. Carried from JoinRequest on
    # approval, or stamped by complete_onboarding when collected inline.
    sms_consent_at = models.DateTimeField(null=True, blank=True)
    calendar_token = models.CharField(max_length=64, blank=True, default="", db_index=True)
    bio = models.CharField(max_length=500, blank=True, default="")
    profile_photo = models.ImageField(upload_to="profile_photos/", blank=True)
    show_phone = models.BooleanField(default=True)
    show_email = models.BooleanField(default=True)
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
    first_name = None
    last_name = None

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = ["display_name"]
    objects = UserManager()

    def __str__(self):
        return self.display_name or self.phone_number

    def has_permission(self, key: str) -> bool:
        """Return True if any of the user's roles grants this permission key.

        Uses the prefetch cache when available (avoids N+1 in list views),
        otherwise falls back to a queryset.
        """
        cache = getattr(self, "_prefetched_objects_cache", {})
        roles = cache["roles"] if "roles" in cache else self.roles.all()
        for role in roles:
            if role.name == "admin" and role.is_default:
                return True
            if key in (role.permissions or []):
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


@receiver(post_save, sender=User)
def assign_admin_role_to_superuser(sender, instance, created, **kwargs):
    """Automatically assign the admin role to any newly created superuser."""
    if created and instance.is_superuser:
        try:
            admin_role = Role.objects.get(name="admin", is_default=True)
            instance.roles.add(admin_role)
        except Role.DoesNotExist:
            pass
