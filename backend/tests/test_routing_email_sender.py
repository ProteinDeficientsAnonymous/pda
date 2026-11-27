from unittest.mock import Mock

import pytest
from notifications._console_sender import ConsoleSender
from notifications._resend_sender import ResendSender
from notifications._routing_email_sender import RoutingEmailSender
from notifications.email_types import BatchSendResult


def _router(provider_result: BatchSendResult | None = None):
    provider = Mock(send_batch=Mock(return_value=provider_result or BatchSendResult(accepted=1)))
    return RoutingEmailSender(provider=provider, log_only=ConsoleSender()), provider


def test_routing_batch_splits_test_domain():
    router, provider = _router()
    result = router.send_batch(["a@example.com", "b@staging.example"], "s", "<p>h</p>", "t")
    assert provider.send_batch.call_args.args[0] == ["a@example.com"]
    assert result.accepted == 2


def test_routing_batch_all_test_domain_skips_provider():
    router, provider = _router()
    result = router.send_batch(["a@staging.example"], "s", "<p>h</p>", "t")
    provider.send_batch.assert_not_called()
    assert result.accepted == 1


def test_routing_batch_no_test_domain_skips_log_only():
    log_only = Mock()
    provider = Mock(send_batch=Mock(return_value=BatchSendResult(accepted=1, failed=1)))
    router = RoutingEmailSender(provider=provider, log_only=log_only)
    result = router.send_batch(["a@example.com"], "s", "h", "t")
    log_only.send_batch.assert_not_called()
    assert result == BatchSendResult(accepted=1, failed=1)


def test_console_batch_accepts_all():
    result = ConsoleSender().send_batch(["a@example.com", "b@example.com"], "s", "h", "t")
    assert result == BatchSendResult(accepted=2)


def test_console_batch_logs_masked_recipient(caplog):
    caplog.set_level("INFO", logger="notifications.console_sender")
    ConsoleSender().send_batch(["a@example.com"], "s", "h", "t")
    assert "a@example.com" not in caplog.text
    assert "sha256:" in caplog.text


def test_console_batch_counts_invalid_recipient_failed():
    result = ConsoleSender().send_batch(["a@example.com", "not-an-email"], "s", "h", "t")
    assert result == BatchSendResult(accepted=1, failed=1)


def test_routing_batch_leaves_validation_to_the_senders():
    router, provider = _router()
    router.send_batch(["not-an-email", "a@example.com"], "s", "h", "t")
    assert provider.send_batch.call_args.args[0] == ["not-an-email", "a@example.com"]


def test_resend_batch_not_supported():
    with pytest.raises(NotImplementedError):
        ResendSender.send_batch(Mock(), ["a@example.com"], "s", "h", "t")
