import uuid

from django.db import models


class JoinRequestStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class JoinRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    email = models.EmailField()
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
        return f"{self.name} ({self.email}) — {self.submitted_at:%Y-%m-%d}"


class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    location = models.CharField(max_length=300, blank=True)
    whatsapp_link = models.URLField(blank=True)
    partiful_link = models.URLField(blank=True)
    rsvp_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
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
