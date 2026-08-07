"""Survey, SurveyQuestion, SurveyResponse, SurveyAnswer, DatetimePollResult models."""

import uuid
from typing import TYPE_CHECKING

from django.db import models

from community.models.choices import SurveyQuestionType, SurveyVisibility

if TYPE_CHECKING:
    from django.db.models import Manager


class Survey(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="", max_length=2000)
    slug = models.SlugField(max_length=100, unique=True)
    visibility = models.CharField(
        max_length=20,
        choices=SurveyVisibility.choices,
        default=SurveyVisibility.PUBLIC,
    )
    is_active = models.BooleanField(default=True)
    one_response_per_user = models.BooleanField(default=False)
    linked_event = models.ForeignKey(
        "community.Event",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="surveys",
    )
    created_by = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_surveys",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    if TYPE_CHECKING:
        linked_event_id: uuid.UUID | None
        created_by_id: uuid.UUID | None
        questions: "Manager[SurveyQuestion]"
        responses: "Manager[SurveyResponse]"
        poll_result: "DatetimePollResult"

    class Meta:
        app_label = "community"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class SurveyQuestion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name="questions")
    label = models.CharField(max_length=500)
    field_type = models.CharField(
        max_length=20,
        choices=SurveyQuestionType.choices,
        default=SurveyQuestionType.TEXT,
    )
    options = models.JSONField(default=list, blank=True)
    required = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        app_label = "community"
        ordering = ["display_order"]

    def __str__(self):
        return f"{self.survey.title}: {self.label}"


class SurveyResponse(models.Model):
    if TYPE_CHECKING:
        user_id: uuid.UUID | None
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name="responses")
    user = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="survey_responses",
    )
    answers = models.JSONField(default=dict, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "community"
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"Response to {self.survey.title} ({self.submitted_at:%Y-%m-%d})"


class DatetimePollResult(models.Model):
    if TYPE_CHECKING:
        finalized_by_id: uuid.UUID | None
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    survey = models.OneToOneField(Survey, on_delete=models.CASCADE, related_name="poll_result")
    winning_datetime = models.DateTimeField()
    finalized_by = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="finalized_polls",
    )
    finalized_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "community"

    def __str__(self):
        return f"Poll result for {self.survey.title}: {self.winning_datetime:%Y-%m-%d %H:%M}"
