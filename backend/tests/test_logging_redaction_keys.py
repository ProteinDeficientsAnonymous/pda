import logging

import pytest
from config.logging_config import JsonFormatter, SensitiveDataFilter


def _record(msg: str, **extra: object) -> logging.LogRecord:
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg=msg,
        args=None,
        exc_info=None,
    )
    record.__dict__.update(extra)
    return record


class TestPrefixedAndCompoundKeys:
    """Credentials are usually logged as `access_token`, `x-api-key`, `session_id`
    — a keyword glued to a `_`/`-`-separated prefix or suffix. The boundary must
    catch those without re-redacting benign letter-glued words (`telephone`)."""

    @pytest.mark.parametrize(
        "message",
        [
            "access_token=AKIAsecretvalue",
            "refresh_token=rt_secretvalue",
            "client_secret=clientsecretval",
            "csrf_token=csrfsecretval",
            "id_token=idsecretval",
            "user_password=hunter2secret",
            "session_id=sessionsecretval",
            "password_hash=hashsecretval",
            "X-Api-Key: live_sk_secretval",
            "x-api-key=apisecretval",
            "X-Auth-Token: authsecretval",
        ],
    )
    def test_redacts_prefixed_credential_keys_in_message(self, message):
        secret = message.split("=", 1)[-1].split(": ", 1)[-1]
        f = SensitiveDataFilter()
        record = _record(message)
        f.filter(record)
        assert secret not in record.msg
        assert "[REDACTED]" in record.msg

    @pytest.mark.parametrize(
        "key",
        ["access_token", "refresh_token", "client_secret", "session_id", "csrf_token"],
    )
    def test_redacts_prefixed_credential_keys_in_extras(self, key):
        # logger.info("auth", extra={"access_token": "..."}) — the exact key name
        # is a compound the old ^keyword$ matcher missed entirely.
        f = SensitiveDataFilter()
        record = _record("auth", **{key: "rawsecretvalue"})
        f.filter(record)
        output = JsonFormatter().format(record)
        assert "rawsecretvalue" not in output
        assert "[REDACTED]" in output

    @pytest.mark.parametrize(
        "message",
        ["status_code: 200", "discount_code=SAVE10", "telephone: support line"],
    )
    def test_does_not_over_redact_benign_compound_words(self, message):
        # No credential keyword appears as a separator-bounded segment, so these
        # must survive even though they share letters with keywords.
        f = SensitiveDataFilter()
        record = _record(message)
        f.filter(record)
        assert record.msg == message

    @pytest.mark.parametrize(
        "key",
        ["telephone", "geocode", "passwordless_hint", "iphone", "username"],
    )
    def test_does_not_redact_benign_compound_extra_keys(self, key):
        f = SensitiveDataFilter()
        record = _record("event", **{key: "kept-value"})
        f.filter(record)
        assert record.__dict__[key] == "kept-value"

    def test_redacts_each_pair_in_multi_credential_cookie_line(self):
        # A Cookie header logged as one string carries several secrets; each must
        # be redacted independently, not just the first.
        f = SensitiveDataFilter()
        record = _record("Cookie: sessionid=SECRET1; csrftoken=SECRET2; foo=bar")
        f.filter(record)
        assert "SECRET1" not in record.msg
        assert "SECRET2" not in record.msg
        assert "foo=bar" in record.msg


class TestNonStringExtraRedaction:
    """`JsonFormatter` serializes extras with `json.dumps(default=str)`, so any
    secret inside a bytes payload or a custom object's str() would reach the output
    after the filter ran unless the filter redacts the text form too."""

    def test_redacts_secret_in_bytes_extra(self):
        f = SensitiveDataFilter()
        record = _record("request", body=b"password=secretbytesvalue")
        f.filter(record)
        output = JsonFormatter().format(record)
        assert "secretbytesvalue" not in output
        assert "[REDACTED]" in output

    def test_redacts_secret_in_object_str_extra(self):
        class Payload:
            def __str__(self) -> str:
                return "User(token=objectsecretvalue)"

        f = SensitiveDataFilter()
        record = _record("request", data=Payload())
        f.filter(record)
        output = JsonFormatter().format(record)
        assert "objectsecretvalue" not in output
        assert "[REDACTED]" in output

    def test_preserves_numeric_and_none_extras(self):
        # Plain scalars must pass through untouched (not stringified/redacted).
        f = SensitiveDataFilter()
        record = _record("done", count=42, ratio=1.5, ok=True, missing=None)
        f.filter(record)
        assert record.count == 42  # type: ignore[attr-defined]
        assert record.ratio == 1.5  # type: ignore[attr-defined]
        assert record.ok is True  # type: ignore[attr-defined]
        assert record.missing is None  # type: ignore[attr-defined]

    def test_redacts_sensitive_key_with_non_string_value(self):
        # A sensitive key name wins regardless of value type.
        f = SensitiveDataFilter()
        record = _record("auth", otp=123456)
        f.filter(record)
        assert record.otp == "[REDACTED]"  # type: ignore[attr-defined]


class TestFilterIdempotency:
    def test_second_filter_pass_is_a_noop(self):
        # The filter may run more than once on a shared record; re-redaction must
        # not corrupt already-redacted output.
        f = SensitiveDataFilter()
        record = _record("access_token=secretval", header={"authorization": "Bearer x"})
        f.filter(record)
        first_msg = record.msg
        first_header = dict(record.header)  # type: ignore[attr-defined]
        f.filter(record)
        assert record.msg == first_msg
        assert record.header == first_header  # type: ignore[attr-defined]


class TestFullValueRedaction:
    """A sensitive value is redacted in full — including spaces and arbitrary auth
    schemes — but redaction stops at pair delimiters so each k=v on a cookie/query
    line is scrubbed independently rather than swallowing the rest of the line."""

    @pytest.mark.parametrize(
        "message,leaked",
        [
            ("password: my secret pass phrase", "pass phrase"),
            ("secret=p@ss w0rd here", "w0rd here"),
            ("token: abc def ghi", "def ghi"),
            # Non-Bearer/Basic schemes must not leave the credential after the scheme word.
            ("Authorization: Negotiate longBase64CredentialXYZ", "longBase64CredentialXYZ"),
            ("Authorization: Digest opaqueDigestSecret", "opaqueDigestSecret"),
        ],
    )
    def test_redacts_space_containing_values_in_full(self, message, leaked):
        f = SensitiveDataFilter()
        record = _record(message)
        f.filter(record)
        assert leaked not in record.msg
        assert "[REDACTED]" in record.msg

    @pytest.mark.parametrize(
        "message,leaked,kept",
        [
            (
                "Cookie: sessionid=SECRET1; csrftoken=SECRET2; foo=bar",
                ["SECRET1", "SECRET2"],
                "foo=bar",
            ),
            ("a=1&token=SECRET3&b=2", ["SECRET3"], "b=2"),
            ("password=p1, user=bob", ["p1"], "user=bob"),
        ],
    )
    def test_redacts_each_pair_but_keeps_non_secret_tail(self, message, leaked, kept):
        f = SensitiveDataFilter()
        record = _record(message)
        f.filter(record)
        for secret in leaked:
            assert secret not in record.msg
        assert kept in record.msg


class TestRedactionFailsSafe:
    """Redaction must never raise out of the logging call. An extra whose __str__
    explodes is suppressed, not propagated, and no partial content leaks."""

    def test_raising_str_does_not_crash_and_suppresses_content(self):
        class Boom:
            def __str__(self) -> str:
                raise RuntimeError("str exploded")

        f = SensitiveDataFilter()
        record = _record("processing payload", payload=Boom())
        # Must not raise.
        result = f.filter(record)
        assert result is True
        output = JsonFormatter().format(record)
        assert "REDACT" in output  # content was replaced with a redaction marker
        # The exploding object is gone (replaced before json.dumps stringifies it).
        assert record.payload == "[REDACTED]"  # type: ignore[attr-defined]

    def test_raising_str_in_message_args_is_suppressed(self):
        class Boom:
            def __str__(self) -> str:
                raise RuntimeError("str exploded")

        f = SensitiveDataFilter()
        # %-arg whose rendering raises inside getMessage().
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="value=%s",
            args=(Boom(),),
            exc_info=None,
        )
        assert f.filter(record) is True
        assert record.args == ()
        assert "exploded" not in str(record.msg)
