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
    email = models.EmailField(blank=True)
    roles = models.ManyToManyField(Role, blank=True, related_name="users")
    needs_onboarding = models.BooleanField(default=False)
    onboarded_at = models.DateTimeField(null=True, blank=True)
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

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    @classmethod
    def create_for_user(cls, user: "User") -> "MagicLoginToken":
        return cls.objects.create(
            user=user,
            expires_at=timezone.now() + timedelta(days=7),
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
