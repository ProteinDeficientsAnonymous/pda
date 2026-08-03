"""TextChoices enums and plain constants for the community app."""

from typing import NamedTuple

from django.db import models


class PageVisibility(models.TextChoices):
    PUBLIC = "public", "Public"
    MEMBERS_ONLY = "members_only", "Members only"
    INVITE_ONLY = "invite_only", "Invite only"


class EventType(models.TextChoices):
    OFFICIAL = "official", "Official"
    COMMUNITY = "community", "Community"
    CLUB = "club", "Club"


class EventStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    CANCELLED = "cancelled", "Cancelled"
    DELETED = "deleted", "Deleted"


class EventFlagStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    DISMISSED = "dismissed", "Dismissed"
    ACTIONED = "actioned", "Actioned"


class CoHostInviteStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ACCEPTED = "accepted", "Accepted"
    DECLINED = "declined", "Declined"
    RESCINDED = "rescinded", "Rescinded"
    EXPIRED = "expired", "Expired"
    REMOVED = "removed", "Removed"


class JoinRequestStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    TENTATIVE = "tentative", "Tentatively approved"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class SurveyVisibility(models.TextChoices):
    PUBLIC = "public", "Public"
    MEMBERS_ONLY = "members_only", "Members only"


class QuestionTypeDefinition(NamedTuple):
    value: str
    label: str


class QuestionType:
    TEXT = QuestionTypeDefinition("text", "Text")
    TEXTAREA = QuestionTypeDefinition("textarea", "Text area")
    SELECT = QuestionTypeDefinition("select", "Single select")
    MULTISELECT = QuestionTypeDefinition("multiselect", "Multi select")
    DROPDOWN = QuestionTypeDefinition("dropdown", "Dropdown")
    NUMBER = QuestionTypeDefinition("number", "Number")
    YES_NO = QuestionTypeDefinition("yes_no", "Yes / No")
    RATING = QuestionTypeDefinition("rating", "Rating")
    DATETIME_POLL = QuestionTypeDefinition("datetime_poll", "Datetime poll")


class SurveyQuestionType(models.TextChoices):
    TEXT = QuestionType.TEXT.value, QuestionType.TEXT.label
    TEXTAREA = QuestionType.TEXTAREA.value, QuestionType.TEXTAREA.label
    SELECT = QuestionType.SELECT.value, QuestionType.SELECT.label
    MULTISELECT = QuestionType.MULTISELECT.value, QuestionType.MULTISELECT.label
    DROPDOWN = QuestionType.DROPDOWN.value, QuestionType.DROPDOWN.label
    NUMBER = QuestionType.NUMBER.value, QuestionType.NUMBER.label
    YES_NO = QuestionType.YES_NO.value, QuestionType.YES_NO.label
    RATING = QuestionType.RATING.value, QuestionType.RATING.label
    DATETIME_POLL = QuestionType.DATETIME_POLL.value, QuestionType.DATETIME_POLL.label


class JoinFormQuestionType(models.TextChoices):
    """Question types supported by join forms."""

    TEXT = QuestionType.TEXT.value, QuestionType.TEXT.label
    TEXTAREA = QuestionType.TEXTAREA.value, QuestionType.TEXTAREA.label
    DROPDOWN = QuestionType.DROPDOWN.value, QuestionType.DROPDOWN.label


class InvitePermission(models.TextChoices):
    ALL_MEMBERS = "all_members", "All members"
    CO_HOSTS_ONLY = "co_hosts_only", "Co-hosts only"


class RSVPStatus(models.TextChoices):
    ATTENDING = "attending", "Attending"
    MAYBE = "maybe", "Maybe"
    CANT_GO = "cant_go", "Can't go"
    WAITLISTED = "waitlisted", "Waitlisted"
    REMOVED = "removed", "Removed"


class AttendanceStatus(models.TextChoices):
    UNKNOWN = "unknown", "Unknown"
    ATTENDED = "attended", "Attended"
    NO_SHOW = "no_show", "No show"


class PollAvailability:
    YES = "yes"
    MAYBE = "maybe"
    NO = "no"
    VALID = {YES, MAYBE, NO}


class FeedbackType(models.TextChoices):
    """Categories a user can tag feedback with. Not DB-backed — these are the
    accepted values on the feedback API payload, mapped to GitHub issue labels
    in ``community._feedback``."""

    BUG = "bug", "Bug"
    FEATURE_REQUEST = "feature request", "Feature request"
    IMPROVEMENT = "improvement", "Improvement"


class FeatureFlag(models.TextChoices):
    """Registry of feature flags; pair each member with a default in FLAG_DEFAULTS."""

    HOST_ATTENDANCE_REPORT = "host_attendance_report", "Host attendance report"
    ADMIN_ATTENDANCE_ANALYTICS = "admin_attendance_analytics", "Admin attendance analytics"
    EVENT_PAYMENT_CONFIRMATION = "event_payment_confirmation", "Event payment confirmation"


FLAG_DEFAULTS: dict[str, bool] = {
    FeatureFlag.HOST_ATTENDANCE_REPORT: False,
    FeatureFlag.ADMIN_ATTENDANCE_ANALYTICS: False,
    FeatureFlag.EVENT_PAYMENT_CONFIRMATION: False,
}
