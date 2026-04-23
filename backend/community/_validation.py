"""Machine-readable validation errors.

Validators raise ``ValidationException(code, field, params?)`` instead of
``ValueError("free text")``. The global Ninja handler (see ``config/urls.py``)
catches both ``ValidationException`` and Pydantic ``ValidationError`` and
reshapes them to ``{ detail: [{code, field, params?}, ...] }`` so the frontend
owns the UI copy.

Adding a new validation error:
  1. Add a constant to ``ValidationCode`` (stable string — don't rename once shipped).
  2. Raise ``ValidationException(ValidationCode.YOUR_CODE, field="foo")``.
  3. Add a case in the frontend's ``validationCodes.ts`` messageForCode().
"""

from typing import Any


class ValidationCode:
    """Stable error codes. Strings are part of the API contract — don't rename."""

    # Event form
    START_DATETIME_REQUIRED_UNLESS_TBD = "start_datetime_required_unless_tbd"
    MAX_ATTENDEES_MUST_BE_AT_LEAST_ONE = "max_attendees_must_be_at_least_one"
    URL_INVALID = "url_invalid"
    URL_PATH_REQUIRED = "url_path_required"
    URL_SCHEME_MUST_BE_HTTP_OR_HTTPS = "url_scheme_must_be_http_or_https"
    WHATSAPP_URL_NOT_RECOGNIZED = "whatsapp_url_not_recognized"
    PARTIFUL_URL_NOT_RECOGNIZED = "partiful_url_not_recognized"

    # Event attendance
    ATTENDANCE_INVALID_CHOICE = "attendance_invalid_choice"


class ValidationException(Exception):
    """Raised by validators to signal a machine-readable error.

    ``field`` is the dotted field name (e.g. ``"start_datetime"`` or
    ``"whatsapp_link"``). Leave ``None`` for model-level errors that don't
    belong to a single field.

    ``params`` lets the frontend interpolate values into the rendered
    message (e.g. a list of allowed hosts). Keep them JSON-serializable.
    """

    def __init__(
        self,
        code: str,
        field: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.field = field
        self.params = params or {}
