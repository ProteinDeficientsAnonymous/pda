import json
import logging

import pytest
from config.logging_config import JsonFormatter, SensitiveDataFilter
from config.middleware import RequestLoggingMiddleware
from django.test import Client, RequestFactory


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


class TestRequestLoggingMiddleware:
    @pytest.fixture(autouse=True)
    def _enable_propagation(self):
        """Allow caplog to capture pda.middleware logs during tests."""
        pda_logger = logging.getLogger("pda")
        original = pda_logger.propagate
        pda_logger.propagate = True
        yield
        pda_logger.propagate = original

    def test_logs_api_request_with_method_path_status_duration(self, caplog):
        factory = RequestFactory()
        request = factory.get("/api/test/")

        def get_response(request):
            from django.http import JsonResponse

            return JsonResponse({"ok": True})

        middleware = RequestLoggingMiddleware(get_response)
        with caplog.at_level(logging.INFO, logger="pda.middleware"):
            middleware(request)
        assert len(caplog.records) >= 1
        msg = caplog.records[0].getMessage()
        assert "GET" in msg
        assert "/api/test/" in msg
        assert "200" in msg
        assert "ms" in msg

    @pytest.mark.django_db
    def test_skips_static_file_requests(self, caplog):
        client = Client()
        with caplog.at_level(logging.INFO, logger="pda.middleware"):
            client.get("/static/test.css")
        middleware_logs = [r for r in caplog.records if r.name == "pda.middleware"]
        assert len(middleware_logs) == 0

    def test_middleware_adds_extra_fields(self, caplog):
        factory = RequestFactory()
        request = factory.get("/api/auth/me/")

        def get_response(request):
            from django.http import JsonResponse

            return JsonResponse({"ok": True})

        middleware = RequestLoggingMiddleware(get_response)
        with caplog.at_level(logging.INFO, logger="pda.middleware"):
            middleware(request)
        assert len(caplog.records) >= 1
        record = caplog.records[0]
        assert record.method == "GET"  # type: ignore[attr-defined]
        assert record.path == "/api/auth/me/"  # type: ignore[attr-defined]
        assert record.status_code == 200  # type: ignore[attr-defined]
        assert hasattr(record, "duration_ms")


class TestApplicationEventLogging:
    """Tests for event logging in API views (Task 3)."""

    @pytest.fixture(autouse=True)
    def _enable_propagation(self):
        pda_logger = logging.getLogger("pda")
        original = pda_logger.propagate
        pda_logger.propagate = True
        yield
        pda_logger.propagate = original

    @pytest.mark.django_db
    def test_join_request_submission_logs_at_info(self, caplog):
        from community.models import JoinFormQuestion

        q = JoinFormQuestion.objects.filter(required=True).first()
        answers = {str(q.id): "I love veganism"} if q else {}
        client = Client()
        with caplog.at_level(logging.INFO, logger="pda.community"):
            client.post(
                "/api/community/join-request/",
                data={
                    "display_name": "Alice",
                    "phone_number": "+12025551234",
                    "answers": answers,
                    "sms_consent": True,
                },
                content_type="application/json",
            )
        community_logs = [r for r in caplog.records if r.name == "pda.community"]
        assert any("Join request" in r.getMessage() for r in community_logs)
        info_logs = [r for r in community_logs if r.levelno == logging.INFO]
        assert len(info_logs) >= 1
        # Must not contain PII
        for r in community_logs:
            msg = r.getMessage()
            assert "+12025551234" not in msg

    @pytest.mark.django_db
    def test_auth_failure_logs_at_warning(self, caplog):
        from users.models import User

        User.objects.create_user(phone_number="+14155551234", password="testpass")
        client = Client()
        with caplog.at_level(logging.WARNING, logger="pda.auth"):
            client.post(
                "/api/auth/login/",
                data={"phone_number": "+14155551234", "password": "wrongpass"},
                content_type="application/json",
            )
        auth_logs = [r for r in caplog.records if r.name == "pda.auth"]
        assert any(r.levelno == logging.WARNING for r in auth_logs)

    @pytest.mark.django_db
    def test_email_failure_logs_at_error(self, caplog, settings):
        from community.models import JoinFormQuestion

        settings.VETTING_EMAIL = "test@example.com"
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        q = JoinFormQuestion.objects.filter(required=True).first()
        answers = {str(q.id): "Community"} if q else {}
        client = Client()

        def _fail_send_mail(*args, **kwargs):
            raise Exception("SMTP down")

        with (
            caplog.at_level(logging.ERROR, logger="pda.community"),
            pytest.MonkeyPatch.context() as mp,
        ):
            mp.setattr("community._join_requests.send_mail", _fail_send_mail)
            response = client.post(
                "/api/community/join-request/",
                data={
                    "display_name": "Bob",
                    "phone_number": "+13105551234",
                    "answers": answers,
                    "sms_consent": True,
                },
                content_type="application/json",
            )
        # Join request should still succeed despite email failure
        assert response.status_code == 201
        error_logs = [
            r for r in caplog.records if r.name == "pda.community" and r.levelno == logging.ERROR
        ]
        assert len(error_logs) >= 1


class TestErrorReportEndpoint:
    """Tests for POST /api/community/error-report/ (Task 4)."""

    @pytest.fixture(autouse=True)
    def _enable_propagation(self):
        pda_logger = logging.getLogger("pda")
        original = pda_logger.propagate
        pda_logger.propagate = True
        yield
        pda_logger.propagate = original

    @pytest.mark.django_db
    def test_error_report_requires_auth(self):
        client = Client()
        response = client.post(
            "/api/community/error-report/",
            {"error": "Something broke"},
            content_type="application/json",
        )
        assert response.status_code == 401

    @pytest.mark.django_db
    def test_error_report_logs_at_error_level(self, caplog, auth_headers):
        client = Client()
        with caplog.at_level(logging.ERROR, logger="pda.frontend"):
            response = client.post(
                "/api/community/error-report/",
                {
                    "error": "Unhandled exception in CalendarScreen",
                    "stack_trace": "at CalendarScreen.build line 42",
                    "context": "/calendar",
                },
                content_type="application/json",
                **auth_headers,
            )
        assert response.status_code == 201
        frontend_logs = [r for r in caplog.records if r.name == "pda.frontend"]
        assert len(frontend_logs) >= 1
        assert frontend_logs[0].levelno == logging.ERROR
        assert "CalendarScreen" in frontend_logs[0].getMessage()

    @pytest.mark.django_db
    def test_error_report_accepts_minimal_payload(self, auth_headers):
        client = Client()
        response = client.post(
            "/api/community/error-report/",
            {"error": "Something broke"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 201

    @pytest.mark.django_db
    def test_error_report_logs_enriched_fields(self, caplog, auth_headers):
        client = Client()
        with caplog.at_level(logging.ERROR, logger="pda.frontend"):
            client.post(
                "/api/community/error-report/",
                {
                    "error": "Something broke",
                    "route": "/calendar",
                    "app_version": "abc123",
                    "client_timestamp": "2026-04-06T12:00:00Z",
                },
                content_type="application/json",
                **auth_headers,
            )
        frontend_logs = [r for r in caplog.records if r.name == "pda.frontend"]
        assert len(frontend_logs) >= 1
        record = frontend_logs[0]
        assert record.route == "/calendar"
        assert record.app_version == "abc123"
        assert record.client_timestamp == "2026-04-06T12:00:00Z"
