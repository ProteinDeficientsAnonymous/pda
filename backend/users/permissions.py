from django.db import models


class PermissionKey(models.TextChoices):
    CREATE_USER = "create_user", "Create user"
    MANAGE_USERS = "manage_users", "Manage users"
    MANAGE_ROLES = "manage_roles", "Manage roles"
    APPROVE_JOIN_REQUESTS = "approve_join_requests", "Approve join requests"
    MANAGE_EVENTS = "manage_events", "Manage events"
    MANAGE_GUIDELINES = "manage_guidelines", "Manage community guidelines"
    MANAGE_WHATSAPP = "manage_whatsapp", "Manage WhatsApp configuration"
    EDIT_FAQ = "edit_faq", "Edit FAQ"
    EDIT_HOMEPAGE = "edit_homepage", "Edit homepage"
    EDIT_JOIN_QUESTIONS = "edit_join_questions", "Edit join form questions"
    MANAGE_SURVEYS = "manage_surveys", "Manage surveys"
    TAG_OFFICIAL_EVENT = "tag_official_event", "Tag official event"
