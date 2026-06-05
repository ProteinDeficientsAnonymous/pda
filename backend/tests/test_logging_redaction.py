import json
import logging

import pytest
from config.logging_config import JsonFormatter, SensitiveDataFilter


class TestJsonFormatter:
    def test_format_outputs_valid_json_with_required_fields(self):
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="pda.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=None,
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "pda.test"
        assert parsed["message"] == "Test message"
        assert "timestamp" in parsed

    def test_format_includes_extra_fields(self):
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="pda.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Request completed",
            args=None,
            exc_info=None,
        )
        record.method = "GET"  # type: ignore[attr-defined]
        record.path = "/api/test/"  # type: ignore[attr-defined]
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["method"] == "GET"
        assert parsed["path"] == "/api/test/"

    def test_format_handles_exception_info(self):
        formatter = JsonFormatter()
        try:
            raise ValueError("test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="pda.test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="An error occurred",
            args=None,
            exc_info=exc_info,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert "exception" in parsed
        assert "ValueError: test error" in parsed["exception"]


class TestSensitiveDataFilter:
    def test_redacts_password_values(self):
        f = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="password=secret123",
            args=None,
            exc_info=None,
        )
        f.filter(record)
        assert "secret123" not in record.msg
        assert "[REDACTED]" in record.msg

    def test_redacts_token_values(self):
        f = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="token=eyJhbGciOiJIUzI1NiJ9.payload.sig",
            args=None,
            exc_info=None,
        )
        f.filter(record)
        assert "eyJhbGci" not in record.msg
        assert "[REDACTED]" in record.msg

    def test_redacts_e164_phone_numbers(self):
        f = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="User logged in: +12025551234",
            args=None,
            exc_info=None,
        )
        f.filter(record)
        assert "+12025551234" not in record.msg
        assert "[REDACTED]" in record.msg

    def test_redacts_phone_number_field(self):
        f = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg='phone_number="+12025551234"',
            args=None,
            exc_info=None,
        )
        f.filter(record)
        assert "+12025551234" not in record.msg

    def test_passes_clean_messages_through(self):
        f = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Join request submitted by Alice",
            args=None,
            exc_info=None,
        )
        f.filter(record)
        assert record.msg == "Join request submitted by Alice"

    def test_redacts_authorization_header(self):
        f = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Authorization: Bearer eyJtoken123",
            args=None,
            exc_info=None,
        )
        f.filter(record)
        assert "eyJtoken123" not in record.msg
        assert "[REDACTED]" in record.msg

    def test_redacts_secret_in_format_args(self):
        f = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="token=%s",
            args=("abc123secret",),
            exc_info=None,
        )
        f.filter(record)
        # Args are collapsed and the rendered message is redacted.
        assert record.args == ()
        assert "abc123secret" not in record.getMessage()
        assert "[REDACTED]" in record.getMessage()

    def test_redacts_phone_in_format_args(self):
        f = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="user logged in: %s",
            args=("+12025551234",),
            exc_info=None,
        )
        f.filter(record)
        assert record.args == ()
        assert "+12025551234" not in record.getMessage()
        assert "[REDACTED]" in record.getMessage()

    def test_redacts_sensitive_extra_string(self):
        f = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="login attempt",
            args=None,
            exc_info=None,
        )
        record.detail = "password=hunter2"  # type: ignore[attr-defined]
        f.filter(record)
        output = JsonFormatter().format(record)
        assert "hunter2" not in output
        assert "[REDACTED]" in output

    def test_redacts_sensitive_extra_by_key_name(self):
        f = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="login attempt",
            args=None,
            exc_info=None,
        )
        # Simulates logger.info("login attempt", extra={"password": "hunter2"}).
        record.password = "hunter2"  # type: ignore[attr-defined]
        f.filter(record)
        output = JsonFormatter().format(record)
        assert "hunter2" not in output
        assert "[REDACTED]" in output

    def test_redacts_sensitive_extra_nested_dict(self):
        f = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="request",
            args=None,
            exc_info=None,
        )
        record.headers = {"authorization": "Bearer topsecret"}  # type: ignore[attr-defined]
        f.filter(record)
        output = JsonFormatter().format(record)
        assert "topsecret" not in output
        assert "[REDACTED]" in output

    def test_preserves_non_string_extras(self):
        f = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="request completed",
            args=None,
            exc_info=None,
        )
        record.status_code = 200  # type: ignore[attr-defined]
        record.duration_ms = 12.5  # type: ignore[attr-defined]
        f.filter(record)
        assert record.status_code == 200  # type: ignore[attr-defined]
        assert record.duration_ms == 12.5  # type: ignore[attr-defined]

    @pytest.mark.parametrize(
        "keyword",
        [
            "api_key",
            "apikey",
            "jwt",
            "session",
            "cookie",
            "set-cookie",
            "refresh",
            "otp",
            "verification_code",
            "auth_code",
            "reset_code",
        ],
    )
    def test_redacts_new_sensitive_keywords(self, keyword):
        f = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=f"{keyword}=supersecretvalue",
            args=None,
            exc_info=None,
        )
        f.filter(record)
        assert "supersecretvalue" not in record.msg
        assert "[REDACTED]" in record.msg

    def test_redacts_multiple_pairs_independently(self):
        f = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="token=abc123 user=alice otp=999999",
            args=None,
            exc_info=None,
        )
        f.filter(record)
        # The non-sensitive value in the middle must survive.
        assert "user=alice" in record.msg
        assert "abc123" not in record.msg
        assert "999999" not in record.msg

    @pytest.mark.parametrize(
        "message",
        [
            "HTTP code: 500",
            "error code: 42",
            "status_code: 200",
            "geocode: failed",
            "discount_code=SAVE10",
        ],
    )
    def test_does_not_over_redact_diagnostic_code_lines(self, message):
        # Benign operational lines containing the word "code" must pass through
        # untouched — the bare "code" keyword over-redacted these previously.
        f = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=message,
            args=None,
            exc_info=None,
        )
        f.filter(record)
        assert record.msg == message
        assert "[REDACTED]" not in record.msg

    def test_keyword_match_respects_word_boundaries(self):
        # "phone" inside "telephone" / "code" inside "geocode" must not match.
        f = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="telephone: support line",
            args=None,
            exc_info=None,
        )
        f.filter(record)
        assert record.msg == "telephone: support line"

    def test_redacts_secret_in_positionally_logged_dict(self):
        # logger.info("payload: %s", {"otp": "123456", "password": "hunter2"})
        # renders the dict via repr, so the keys are quoted ('otp': ...). The
        # redaction must still strip the values from the rendered string.
        f = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="payload: %s",
            args=({"otp": "123456", "password": "hunter2"},),
            exc_info=None,
        )
        f.filter(record)
        assert record.args == ()
        rendered = record.getMessage()
        assert "123456" not in rendered
        assert "hunter2" not in rendered
        assert "[REDACTED]" in rendered

    def test_redacts_double_quoted_json_keys(self):
        # JSON-style serialization quotes keys with double quotes.
        f = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg='body: {"token": "abc123secret"}',
            args=None,
            exc_info=None,
        )
        f.filter(record)
        assert "abc123secret" not in record.msg
        assert "[REDACTED]" in record.msg
