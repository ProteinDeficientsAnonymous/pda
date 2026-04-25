"""Machine-readable validation errors.

Validators raise ``ValidationException(code, field, params?)`` instead of
``ValueError("free text")``. The global Ninja handler (see
``config/validation_handlers.py``) catches both ``ValidationException`` and
Ninja's wrapped Pydantic errors and reshapes them to
``{ detail: [{code, field, params?}, ...] }`` so the frontend owns UI copy.

Code strings are part of the API contract — **never rename** once shipped.
Organize codes under ``Code.<Domain>.<NAME>``; the frontend mirrors this.

Adding a new code:
  1. Add a constant under the right ``Code.<Domain>`` class.
  2. ``raise_validation(Code.Domain.NAME, field="foo")`` (or
     ``raise ValidationException(...)`` if you need custom args).
  3. Add a ``case`` in the frontend's ``validationCodes.ts``
     ``messageForCode()``.
"""

from typing import Any, NoReturn


class Code:
    """Namespaced validation code catalog. Strings are the wire format."""

    class Event:
        NOT_FOUND = "event.not_found"
        START_DATETIME_REQUIRED_UNLESS_TBD = "event.start_datetime_required_unless_tbd"
        MAX_ATTENDEES_MUST_BE_AT_LEAST_ONE = "event.max_attendees_must_be_at_least_one"
        START_DATETIME_MUST_BE_FUTURE = "event.start_datetime_must_be_future"
        END_BEFORE_START = "event.end_before_start"
        ATTENDANCE_INVALID_CHOICE = "event.attendance_invalid_choice"
        OFFICIAL_MUST_BE_PUBLIC = "event.official_must_be_public"
        INVALID_CREATE_STATUS = "event.invalid_create_status"
        DATE_LOCKED_BY_POLL = "event.date_locked_by_poll"
        INVITE_ONLY = "event.invite_only"
        AUTH_REQUIRED = "event.auth_required"
        CANCELLED_CANNOT_BE_EDITED = "event.cancelled_cannot_be_edited"
        PAST_CANNOT_BE_CANCELLED = "event.past_cannot_be_cancelled"
        NO_ATTENDEES_CANNOT_BE_CANCELLED = "event.no_attendees_cannot_be_cancelled"
        INVALID_STATUS_TRANSITION = "event.invalid_status_transition"
        CANCEL_BEFORE_DELETE = "event.cancel_before_delete"
        FLAG_ALREADY_FLAGGED = "event.flag_already_flagged"
        FLAG_INVALID_ACTION = "event.flag_invalid_action"
        RSVPS_NOT_ENABLED = "event.rsvps_not_enabled"
        RSVPS_CLOSED_CANCELLED = "event.rsvps_closed_cancelled"
        RSVPS_CLOSED_PAST = "event.rsvps_closed_past"
        RSVP_INVALID_STATUS = "event.rsvp_invalid_status"
        NO_PLUS_ONE_SPOTS = "event.no_plus_one_spots"
        RSVP_NOT_FOUND = "event.rsvp_not_found"
        ATTENDANCE_OPENS_LATER = "event.attendance_opens_later"
        ATTENDANCE_ONLY_FOR_GOING_RSVPS = "event.attendance_only_for_going_rsvps"
        PERM_DENIED = "event.perm_denied"  # params: { action?: str }

    class Poll:
        NOT_FOUND = "poll.not_found"
        OPTIONS_REQUIRED = "poll.options_required"
        OPTIONS_MUST_BE_FUTURE = "poll.options_must_be_future"
        EVENT_ALREADY_HAS_POLL = "poll.event_already_has_poll"
        OPTION_NOT_FOUND = "poll.option_not_found"
        OPTION_ALREADY_EXISTS = "poll.option_already_exists"
        CANNOT_MODIFY_FINALIZED = "poll.cannot_modify_finalized"
        ALREADY_FINALIZED = "poll.already_finalized"
        WINNING_OPTION_NOT_FOUND = "poll.winning_option_not_found"
        MIN_TWO_OPTIONS = "poll.min_two_options"
        INVALID_AVAILABILITY = "poll.invalid_availability"

    class Url:
        INVALID = "url.invalid"
        PATH_REQUIRED = "url.path_required"
        SCHEME_MUST_BE_HTTP_OR_HTTPS = "url.scheme_must_be_http_or_https"
        WHATSAPP_NOT_RECOGNIZED = "url.whatsapp_not_recognized"
        PARTIFUL_NOT_RECOGNIZED = "url.partiful_not_recognized"

    class Phone:
        INVALID = "phone.invalid"
        ALREADY_EXISTS = "phone.already_exists"

    class Zelle:
        INVALID = "zelle.invalid"

    class DisplayName:
        REQUIRED = "display_name.required"
        TOO_LONG = "display_name.too_long"  # params: { max_length: int }
        INVALID_CHARS = "display_name.invalid_chars"
        NEEDS_A_LETTER = "display_name.needs_a_letter"

    class Auth:
        INVALID_CREDENTIALS = "auth.invalid_credentials"
        ACCOUNT_ARCHIVED = "auth.account_archived"
        ACCOUNT_PAUSED = "auth.account_paused"
        MAGIC_LINK_INVALID_OR_EXPIRED = "auth.magic_link_invalid_or_expired"
        MAGIC_LINK_ALREADY_USED = "auth.magic_link_already_used"
        ALREADY_SIGNED_IN_AS_DIFFERENT_USER = "auth.already_signed_in_as_different_user"
        REFRESH_TOKEN_INVALID = "auth.refresh_token_invalid"
        REFRESH_FAILED = "auth.refresh_failed"
        CURRENT_PASSWORD_INCORRECT = "auth.current_password_incorrect"

    class Password:
        INVALID = "password.invalid"  # params: { reasons: string[] }

    class Role:
        NOT_FOUND = "role.not_found"
        NAME_ALREADY_EXISTS = "role.name_already_exists"
        PROTECTED_CANNOT_EDIT = "role.protected_cannot_edit"
        PROTECTED_CANNOT_RENAME = "role.protected_cannot_rename"
        PROTECTED_CANNOT_DELETE = "role.protected_cannot_delete"
        CANNOT_REMOVE_OWN_ADMIN = "role.cannot_remove_own_admin"
        CANNOT_REMOVE_LAST_ADMIN = "role.cannot_remove_last_admin"
        MEMBER_ROLE_REQUIRED = "role.member_role_required"

    class Member:
        NOT_FOUND = "member.not_found"

    class User:
        NOT_FOUND = "user.not_found"
        CANNOT_DELETE_SELF = "user.cannot_delete_self"
        CANNOT_DELETE_LAST_ADMIN = "user.cannot_delete_last_admin"
        ALREADY_ARCHIVED = "user.already_archived"
        CANNOT_PAUSE_SELF = "user.cannot_pause_self"
        CANNOT_PAUSE_ADMIN = "user.cannot_pause_admin"
        ROLE_IDS_NOT_FOUND = "user.role_ids_not_found"

    class Survey:
        NOT_FOUND = "survey.not_found"
        SLUG_ALREADY_EXISTS = "survey.slug_already_exists"
        QUESTION_NOT_FOUND = "survey.question_not_found"
        NO_DATETIME_POLL_QUESTION = "survey.no_datetime_poll_question"
        WINNING_DATETIME_NOT_IN_OPTIONS = "survey.winning_datetime_not_in_options"
        POLL_ALREADY_FINALIZED = "survey.poll_already_finalized"
        ANSWER_REQUIRED = "survey.answer_required"  # params: { label }
        ANSWER_INVALID_FORMAT = "survey.answer_invalid_format"  # params: { label }
        ANSWER_INVALID_OPTION = "survey.answer_invalid_option"  # params: { label }
        ANSWER_MUST_BE_NUMBER = "survey.answer_must_be_number"  # params: { label }
        ANSWER_MUST_BE_YES_NO = "survey.answer_must_be_yes_no"  # params: { label }
        ANSWER_RATING_OUT_OF_RANGE = "survey.answer_rating_out_of_range"  # params: { label }
        ANSWER_INVALID_DATETIME_OPTION = (
            "survey.answer_invalid_datetime_option"  # params: { label }
        )
        ANSWER_INVALID_AVAILABILITY = (
            "survey.answer_invalid_availability"  # params: { label, value }
        )

    class JoinRequest:
        NOT_FOUND = "join_request.not_found"
        ALREADY_DECIDED = "join_request.already_decided"
        ONLY_REJECTED_CAN_BE_UN_REJECTED = "join_request.only_rejected_can_be_un_rejected"
        PHONE_ALREADY_INVITED = "join_request.phone_already_invited"
        PHONE_ALREADY_PENDING = "join_request.phone_already_pending"
        ANSWER_REQUIRED = "join_request.answer_required"  # params: { label: str }
        ANSWER_TOO_LONG = "join_request.answer_too_long"  # params: { label: str, max: int }
        ANSWER_INVALID_OPTION = "join_request.answer_invalid_option"  # params: { label: str }
        INVALID_STATUS = "join_request.invalid_status"  # params: { allowed: [str] }

    class Photo:
        TYPE_NOT_ALLOWED = "photo.type_not_allowed"  # params: { allowed: string[] }
        TOO_LARGE = "photo.too_large"  # params: { max_mb: int }

    class Perm:
        DENIED = "perm.denied"  # params: { action?: str }

    class Rate:
        LIMITED = "rate.limited"

    class Page:
        MEMBERS_ONLY = "page.members_only"

    class Docs:
        FOLDER_NOT_FOUND = "docs.folder_not_found"
        PARENT_FOLDER_NOT_FOUND = "docs.parent_folder_not_found"
        DOCUMENT_NOT_FOUND = "docs.document_not_found"

    class JoinForm:
        QUESTION_NOT_FOUND = "join_form.question_not_found"

    class Feedback:
        NOT_CONFIGURED = "feedback.not_configured"
        CREATION_FAILED = "feedback.creation_failed"

    class Notification:
        NOT_FOUND = "notification.not_found"

    class CoHostInvite:
        NOT_FOUND = "cohost_invite.not_found"
        NOT_PENDING = "cohost_invite.not_pending"
        NOT_INVITEE = "cohost_invite.not_invitee"
        NOT_HOST = "cohost_invite.not_host"


class ValidationException(Exception):
    """Raised by validators and route handlers to signal a structured error.

    ``field`` is the dotted field name (``"start_datetime"``,
    ``"whatsapp_link"``). ``None`` for model-level or non-field errors
    (auth failures, permission denials, 404s).

    ``params`` lets the frontend interpolate values into the rendered
    message. Must be JSON-serializable.

    ``status_code`` is the HTTP status returned by the global handler.
    Defaults to 422 (appropriate for Pydantic-style validation). Routes
    raising for auth/permission/not-found should override: 401, 403, 404,
    409, 429.

    ``clear_refresh_cookie`` lets auth route handlers signal that the
    error response should clear the refresh cookie. Applied by the global
    handler when building the response (regular raise bypasses the route's
    ``response`` parameter, so side-effects declared here let us keep the
    single-shape wire contract).
    """

    def __init__(
        self,
        code: str,
        field: str | None = None,
        params: dict[str, Any] | None = None,
        status_code: int = 422,
        clear_refresh_cookie: bool = False,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.field = field
        self.params = params or {}
        self.status_code = status_code
        self.clear_refresh_cookie = clear_refresh_cookie


def raise_validation(
    code: str,
    field: str | None = None,
    *,
    status_code: int = 422,
    clear_refresh_cookie: bool = False,
    **params: Any,
) -> NoReturn:
    """Shorthand for ``raise ValidationException(code, field, params, status_code)``.

    Examples:
        ``raise_validation(Code.Role.NOT_FOUND, status_code=404)``
        ``raise_validation(Code.Url.INVALID, field="whatsapp_link")``
        ``raise_validation(Code.Perm.DENIED, status_code=403, action="delete_role")``
    """
    raise ValidationException(
        code,
        field=field,
        params=params or None,
        status_code=status_code,
        clear_refresh_cookie=clear_refresh_cookie,
    )
