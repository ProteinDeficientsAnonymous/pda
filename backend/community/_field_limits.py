"""Shared field length constants for Pydantic schema validation.

Keep in sync with frontend/lib/config/constants.dart (FieldLimit class).
"""


class FieldLimit:
    TITLE = 200
    SHORT_TEXT = 300
    DESCRIPTION = 2000
    CONTENT = 50000
    CONTENT_HTML = 100000  # HTML is more verbose than Delta JSON
    URL = 200
    DISPLAY_NAME = 64
    PHONE = 20
    PASSWORD = 128
    SLUG = 100
    ROLE_NAME = 50
    OPTION_TEXT = 200
    CHOICE = 20
    BOT_SECRET = 256
    PAYMENT_HANDLE = 100
    BIO = 500
