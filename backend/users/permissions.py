from django.db import models


class PermissionKey(models.TextChoices):
    CREATE_USER = "create_user", "Create user"
    MANAGE_USERS = "manage_users", "Manage users"
    MANAGE_ROLES = "manage_roles", "Manage roles"
    APPROVE_JOIN_REQUESTS = "approve_join_requests", "Approve join requests"
    MANAGE_EVENTS = "manage_events", "Manage events"
    MANAGE_GUIDELINES = "manage_guidelines", "Manage community guidelines"
