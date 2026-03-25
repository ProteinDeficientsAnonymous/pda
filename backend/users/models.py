import uuid

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from users.roles import Role  # noqa: F401 — re-exported so Django discovers it in the users app


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, username=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    roles = models.ManyToManyField(Role, blank=True, related_name="users")
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]
    objects = UserManager()

    def save(self, *args, **kwargs):
        self.username = self.email
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email

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
