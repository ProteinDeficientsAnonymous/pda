"""TextChoices enums and plain constants for the community app."""

from django.db import models


class PageVisibility(models.TextChoices):
    PUBLIC = "public", "Public"
    MEMBERS_ONLY = "members_only", "Members only"
    INVITE_ONLY = "invite_only", "Invite only"


class EventType(models.TextChoices):
    OFFICIAL = "official", "Official"
    COMMUNITY = "community", "Community"


class EventStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    CANCELLED = "cancelled", "Cancelled"


class JoinRequestStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class JoinFormQuestionType(models.TextChoices):
    TEXT = "text", "Text"
    SELECT = "select", "Select"


class SurveyVisibility(models.TextChoices):
    PUBLIC = "public", "Public"
    MEMBERS_ONLY = "members_only", "Members only"


class SurveyQuestionType(models.TextChoices):
    TEXT = "text", "Text"
    TEXTAREA = "textarea", "Text area"
    SELECT = "select", "Single select"
    MULTISELECT = "multiselect", "Multi select"
    DROPDOWN = "dropdown", "Dropdown"
    NUMBER = "number", "Number"
    YES_NO = "yes_no", "Yes / No"
    RATING = "rating", "Rating"
    DATETIME_POLL = "datetime_poll", "Datetime poll"


class InvitePermission(models.TextChoices):
    ALL_MEMBERS = "all_members", "All members"
    CO_HOSTS_ONLY = "co_hosts_only", "Co-hosts only"


class RSVPStatus(models.TextChoices):
    ATTENDING = "attending", "Attending"
    MAYBE = "maybe", "Maybe"
    CANT_GO = "cant_go", "Can't go"
    WAITLISTED = "waitlisted", "Waitlisted"


class PollAvailability:
    YES = "yes"
    MAYBE = "maybe"
    NO = "no"
    VALID = {YES, MAYBE, NO}
