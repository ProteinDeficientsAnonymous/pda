import uuid

from django.conf import settings
from django.db import models


class OAuthClient(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client_id = models.CharField(max_length=255, unique=True)
    client_name = models.CharField(max_length=255, blank=True)
    info = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "mcp_gateway"

    def __str__(self) -> str:
        return self.client_name or self.client_id


class OAuthAuthRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        DENIED = "denied", "Denied"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(OAuthClient, on_delete=models.CASCADE, related_name="auth_requests")
    params = models.JSONField()
    status = models.CharField(max_length=16, choices=Status, default=Status.PENDING)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="mcp_auth_requests",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        app_label = "mcp_gateway"


class OAuthGrant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mcp_grants"
    )
    client = models.ForeignKey(OAuthClient, on_delete=models.CASCADE, related_name="grants")
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "mcp_gateway"


class OAuthAuthCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code_hash = models.CharField(max_length=64, unique=True)
    grant = models.ForeignKey(OAuthGrant, on_delete=models.CASCADE, related_name="auth_codes")
    scopes = models.JSONField(default=list)
    code_challenge = models.CharField(max_length=255)
    redirect_uri = models.TextField()
    redirect_uri_provided_explicitly = models.BooleanField(default=True)
    resource = models.TextField(blank=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "mcp_gateway"


class OAuthToken(models.Model):
    class Kind(models.TextChoices):
        ACCESS = "access", "Access"
        REFRESH = "refresh", "Refresh"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    token_hash = models.CharField(max_length=64, unique=True)
    kind = models.CharField(max_length=16, choices=Kind)
    grant = models.ForeignKey(OAuthGrant, on_delete=models.CASCADE, related_name="tokens")
    scopes = models.JSONField(default=list)
    resource = models.TextField(blank=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "mcp_gateway"
