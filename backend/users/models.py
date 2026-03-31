import uuid

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from users.roles import Role  # noqa: F401 — re-exported so Django discovers it in the users app


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
    calendar_token = models.CharField(max_length=64, blank=True, default="", db_index=True)
    profile_photo = models.ImageField(upload_to="profile_photos/", blank=True)
    show_phone = models.BooleanField(default=True)
    show_email = models.BooleanField(default=True)
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


@receiver(post_save, sender=User)
def assign_admin_role_to_superuser(sender, instance, created, **kwargs):
    """Automatically assign the admin role to any newly created superuser."""
    if created and instance.is_superuser:
        try:
            admin_role = Role.objects.get(name="admin", is_default=True)
            instance.roles.add(admin_role)
        except Role.DoesNotExist:
            pass
