import uuid
from typing import TYPE_CHECKING

from django.db import models

if TYPE_CHECKING:
    from django.db.models import Manager


class JoinRequestStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class JoinRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    display_name = models.CharField(max_length=64)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    pronouns = models.CharField(max_length=100, blank=True)
    how_they_heard = models.TextField(blank=True)
    why_join = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=JoinRequestStatus.choices,
        default=JoinRequestStatus.PENDING,
    )

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.display_name} ({self.phone_number}) — {self.submitted_at:%Y-%m-%d}"


class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=300, blank=True)
    whatsapp_link = models.URLField(blank=True)
    partiful_link = models.URLField(blank=True)
    other_link = models.URLField(blank=True)
    rsvp_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    if TYPE_CHECKING:
        created_by_id: uuid.UUID | None
        rsvps: "Manager[EventRSVP]"
    created_by = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_events",
    )
    co_hosts = models.ManyToManyField(
        "users.User",
        blank=True,
        related_name="co_hosted_events",
    )

    class Meta:
        ordering = ["start_datetime"]

    def __str__(self):
        return f"{self.title} — {self.start_datetime:%Y-%m-%d %H:%M}"


class CommunityGuidelines(models.Model):
    """Singleton model — only one row ever exists (pk=1)."""

    content = models.TextField(default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Community Guidelines"
        verbose_name_plural = "Community Guidelines"

    def __str__(self):
        return "Community Guidelines"

    @classmethod
    def get(cls) -> "CommunityGuidelines":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class FAQ(models.Model):
    """Singleton model — only one row ever exists (pk=1)."""

    content = models.TextField(default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "FAQ"
        verbose_name_plural = "FAQ"

    def __str__(self):
        return "FAQ"

    @classmethod
    def get(cls) -> "FAQ":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class HomePage(models.Model):
    """Singleton model — only one row ever exists (pk=1)."""

    content = models.TextField(default="")
    join_content = models.TextField(default="")
    donate_url = models.URLField(blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Home Page"
        verbose_name_plural = "Home Page"

    def __str__(self):
        return "Home Page"

    @classmethod
    def get(cls) -> "HomePage":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class PageVisibility(models.TextChoices):
    PUBLIC = "public", "Public"
    MEMBERS_ONLY = "members_only", "Members only"


class EditablePage(models.Model):
    """Content pages editable by admins. One row per slug."""

    slug = models.SlugField(max_length=100, unique=True)
    content = models.TextField(default="")
    visibility = models.CharField(
        max_length=20,
        choices=PageVisibility.choices,
        default=PageVisibility.PUBLIC,
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["slug"]

    def __str__(self) -> str:
        return f"EditablePage({self.slug})"

    @classmethod
    def get_or_create_page(
        cls, slug: str, default_visibility: str = PageVisibility.PUBLIC
    ) -> "EditablePage":
        obj, _ = cls.objects.get_or_create(
            slug=slug,
            defaults={"visibility": default_visibility},
        )
        return obj


class WhatsAppConfig(models.Model):
    """Singleton model — only one row ever exists (pk=1).

    Stores WhatsApp bot configuration so admins can update it without redeployment.
    Falls back to Django settings if the DB row has empty values.
    """

    bot_url = models.URLField(blank=True, default="")
    bot_secret = models.CharField(max_length=256, blank=True, default="")
    group_id = models.CharField(max_length=256, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "WhatsApp Configuration"
        verbose_name_plural = "WhatsApp Configuration"

    def __str__(self) -> str:
        return "WhatsApp Configuration"

    @classmethod
    def get(cls) -> "WhatsAppConfig":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class RSVPStatus(models.TextChoices):
    ATTENDING = "attending", "Attending"
    MAYBE = "maybe", "Maybe"
    CANT_GO = "cant_go", "Can't go"


class EventRSVP(models.Model):
    if TYPE_CHECKING:
        user_id: uuid.UUID
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="rsvps")
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="event_rsvps")
    status = models.CharField(max_length=20, choices=RSVPStatus.choices)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("event", "user")]

    def __str__(self):
        return f"{self.user.display_name or self.user.phone_number} → {self.event.title}: {self.status}"
