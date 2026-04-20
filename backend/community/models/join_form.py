"""JoinFormQuestion and JoinRequest models."""

import uuid

from django.conf import settings
from django.db import models

from community.models.choices import JoinFormQuestionType, JoinRequestStatus


class JoinFormQuestion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    label = models.CharField(max_length=300)
    field_type = models.CharField(
        max_length=10,
        choices=JoinFormQuestionType.choices,
        default=JoinFormQuestionType.TEXT,
    )
    options = models.JSONField(default=list, blank=True)
    required = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        app_label = "community"
        ordering = ["display_order"]

    def __str__(self):
        return self.label


class JoinRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    display_name = models.CharField(max_length=64)
    phone_number = models.CharField(max_length=20)
    custom_answers = models.JSONField(default=dict, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=JoinRequestStatus.choices,
        default=JoinRequestStatus.PENDING,
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_join_requests",
    )
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="rejected_join_requests",
    )

    class Meta:
        app_label = "community"
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.display_name} ({self.phone_number}) — {self.submitted_at:%Y-%m-%d}"
