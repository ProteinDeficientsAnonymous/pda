"""DocFolder and Document models."""

import uuid
from typing import TYPE_CHECKING

from django.db import models

if TYPE_CHECKING:
    from django.db.models import Manager


class DocFolder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
    )
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    if TYPE_CHECKING:
        children: "Manager[DocFolder]"
        documents: "Manager[Document]"

    class Meta:
        app_label = "community"
        ordering = ["display_order", "name"]

    def __str__(self):
        return self.name


class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=300)
    # Legacy Quill Delta JSON (Flutter clients). See community/models/content.py
    # for the dual-format design rationale.
    content = models.TextField(default="", max_length=50000)
    content_pm = models.TextField(default="", max_length=50000)
    content_html = models.TextField(default="", max_length=100000)
    folder = models.ForeignKey(
        DocFolder,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    display_order = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_documents",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    if TYPE_CHECKING:
        created_by_id: uuid.UUID | None
        folder_id: uuid.UUID

    class Meta:
        app_label = "community"
        ordering = ["display_order", "title"]

    def __str__(self):
        return self.title
