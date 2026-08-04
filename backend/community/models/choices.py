"""TextChoices enums and plain constants for the community app."""

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


class QuestionType(models.TextChoices):
    """HTML-aligned question type catalog (wire values)."""

    TEXT = "text", "Text"
    TEXTAREA = "textarea", "Text area"
    RADIO = "radio", "Radio"
    SELECT = "select", "Select"
    CHECKBOX = "checkbox", "Checkbox"
    NUMBER = "number", "Number"
    BOOLEAN = "boolean", "Yes / No"
    RATING = "rating", "Rating"
    DATETIME_POLL = "datetime_poll", "Datetime poll"


# Survey authors the full catalog; keep the historical name as an alias.
SurveyQuestionType = QuestionType


class JoinFormQuestionType(models.TextChoices):
    """Question types supported by join forms."""

    TEXT = QuestionType.TEXT.value, QuestionType.TEXT.label
    TEXTAREA = QuestionType.TEXTAREA.value, QuestionType.TEXTAREA.label
    SELECT = QuestionType.SELECT.value, QuestionType.SELECT.label


class RsvpQuestionType(models.TextChoices):
    """Question types supported by event RSVP questions."""

    TEXTAREA = QuestionType.TEXTAREA.value, QuestionType.TEXTAREA.label
    SELECT = QuestionType.SELECT.value, QuestionType.SELECT.label
    CHECKBOX = QuestionType.CHECKBOX.value, QuestionType.CHECKBOX.label


RSVP_QUESTION_TYPE_CHOICES = RsvpQuestionType.choices
RSVP_CHOICE_TYPES = frozenset(
    {RsvpQuestionType.SELECT, RsvpQuestionType.CHECKBOX},
)


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
    DIDNT_GO = "didnt_go", "Didn't go"


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
    WEEKLY_DIGEST_EMAIL = "weekly_digest_email", "Weekly digest email"


FLAG_DEFAULTS: dict[str, bool] = {
    FeatureFlag.HOST_ATTENDANCE_REPORT: False,
    FeatureFlag.ADMIN_ATTENDANCE_ANALYTICS: False,
    FeatureFlag.EVENT_PAYMENT_CONFIRMATION: False,
    FeatureFlag.WEEKLY_DIGEST_EMAIL: False,
}
