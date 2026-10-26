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


def is_official_or_club(event_type: str) -> bool:
    return event_type in (EventType.OFFICIAL, EventType.CLUB)


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


class RejectionReason(models.TextChoices):
    VEGETARIAN = "vegetarian", "person is vegetarian"
    NOT_VEGAN = "not_vegan", "person is not vegan (not vegetarian)"
    QUESTIONS_NOT_ANSWERED = "questions_not_answered", "questions not answered"
    OTHER = "other", "other"


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
    STARS = "stars", "Stars"
    SCALE = "scale", "Scale"
    DATETIME_POLL = "datetime_poll", "Datetime poll"
    SECTION = "section", "Section"


# Survey authors the full catalog; keep the historical name as an alias.
SurveyQuestionType = QuestionType

# Question types whose answers a survey `show_if` condition can compare against.
CONDITION_SOURCE_TYPES = frozenset(
    {QuestionType.RADIO, QuestionType.SELECT, QuestionType.CHECKBOX, QuestionType.BOOLEAN}
)


class ShowIfOperator(models.TextChoices):
    EQUALS = "equals", "Equals"
    NOT_EQUALS = "not_equals", "Not equals"
    CONTAINS = "contains", "Contains"


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


# Guests a payment import can match and verify.
MATCHABLE_RSVP_STATUSES = frozenset({RSVPStatus.ATTENDING, RSVPStatus.WAITLISTED})


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
