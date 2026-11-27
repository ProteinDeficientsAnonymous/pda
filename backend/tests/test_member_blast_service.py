from datetime import timedelta
from unittest.mock import patch

import pytest
from community.validation import Code, ValidationException
from django.conf import settings
from django.utils import timezone
from notifications.email_types import BatchSendResult
from notifications.member_blasts.service import (
    clean_body,
    collect_recipients,
    render_blast,
    send_member_blast,
    send_test_blast,
)
from notifications.models import MemberEmailBlast, MemberEmailBlastStatus
from users.models import MembershipStatus, User

from tests._users import make_attendance_paused, make_user

pytestmark = pytest.mark.django_db


def test_recipients_are_members_with_email():
    included = [
        make_user(membership_status=MembershipStatus.ACTIVE_MEMBER, email="a@x.org"),
        make_user(membership_status=MembershipStatus.GUIDELINES_PAUSED, email="g@x.org"),
        make_attendance_paused(email="p@x.org"),
    ]
    for status in (MembershipStatus.TENTATIVE, MembershipStatus.ARCHIVED, MembershipStatus.NONE):
        make_user(membership_status=status, email=f"{status}@x.org")
    emails, skipped = collect_recipients()
    assert emails == [u.email for u in included]
    assert skipped == 0


def test_member_without_email_is_skipped():
    make_user(membership_status=MembershipStatus.ACTIVE_MEMBER, email="")
    User.objects.filter(pk=make_user(membership_status=MembershipStatus.ACTIVE_MEMBER).pk).update(
        email=None
    )
    assert collect_recipients() == ([], 2)


def test_malformed_email_is_skipped():
    user = make_user(membership_status=MembershipStatus.ACTIVE_MEMBER)
    User.objects.filter(pk=user.pk).update(email="bad@@x")
    assert collect_recipients() == ([], 1)


def test_body_is_sanitized_and_links_absolute():
    out = clean_body(
        '<p onclick="x">hi</p><script>a</script><a href="/events/1">e</a>'
        '<a href="javascript:alert(1)">j</a>'
    )
    assert "script" not in out
    assert "onclick" not in out
    assert "javascript:" not in out
    assert f'href="{settings.FRONTEND_BASE_URL}/events/1"' in out


def test_render_wraps_body_and_footer():
    rendered = render_blast("s", '<p>hi <a href="https://x.org/a">link</a></p>')
    assert "<p>hi " in rendered.html
    assert "because you're a pda member" in rendered.html
    assert "hi link (https://x.org/a)" in rendered.text


def test_render_sanitizes_raw_input():
    rendered = render_blast("s", '<p onclick="x">hi</p><script>a</script>')
    for out in (rendered.html, rendered.text):
        assert "onclick" not in out
        assert "<script>" not in out


@pytest.fixture
def sender_mock():
    with patch("notifications.member_blasts.service.get_email_sender") as get:
        get.return_value.send_batch.return_value = BatchSendResult(accepted=2)
        yield get.return_value.send_batch


@pytest.fixture
def admin():
    return make_user(membership_status=MembershipStatus.ACTIVE_MEMBER, email="admin@x.org")


@pytest.fixture
def two_members(admin):
    make_user(membership_status=MembershipStatus.ACTIVE_MEMBER, email="b@x.org")


def _send(admin, subject="s"):
    return send_member_blast(sender=admin, subject=subject, body_html="<p>hi</p>")


def _assert_refused(code, user):
    with pytest.raises(ValidationException) as exc:
        _send(user)
    assert exc.value.code == code
    assert exc.value.status_code == 400


def test_send_records_sent(admin, two_members, sender_mock):
    blast = _send(admin)
    blast.refresh_from_db()
    assert blast.status == MemberEmailBlastStatus.SENT
    assert blast.recipient_count == 2
    assert blast.finished_at is not None
    assert blast.sender == admin
    sender_mock.assert_called_once()
    assert sorted(sender_mock.call_args.args[0]) == ["admin@x.org", "b@x.org"]


def test_send_unknown_when_brevo_unsure(admin, two_members, sender_mock):
    sender_mock.return_value = BatchSendResult(unknown=2)
    blast = _send(admin)
    assert blast.status == MemberEmailBlastStatus.UNKNOWN
    assert blast.unknown_count == 2


def test_send_failed_allows_resend(admin, two_members, sender_mock):
    sender_mock.return_value = BatchSendResult(failed=2)
    assert _send(admin).status == MemberEmailBlastStatus.FAILED
    sender_mock.return_value = BatchSendResult(accepted=2)
    assert _send(admin).status == MemberEmailBlastStatus.SENT


def test_partly_failed_send_blocks_resend(admin, two_members, sender_mock):
    sender_mock.return_value = BatchSendResult(accepted=1, failed=1)
    assert _send(admin).status == MemberEmailBlastStatus.FAILED
    _assert_refused(Code.Notification.BLAST_DUPLICATE, admin)
    sender_mock.assert_called_once()


def test_send_exception_marks_unknown(admin, two_members, sender_mock):
    sender_mock.side_effect = RuntimeError("boom")
    with pytest.raises(RuntimeError):
        _send(admin)
    blast = MemberEmailBlast.objects.get()
    assert blast.status == MemberEmailBlastStatus.UNKNOWN
    assert blast.unknown_count == blast.recipient_count == 2
    assert blast.finished_at is not None


def test_send_exception_survives_finalize_failure(admin, two_members, sender_mock):
    sender_mock.side_effect = RuntimeError("boom")
    with patch("notifications.member_blasts.service._finalize", side_effect=OSError):
        with pytest.raises(RuntimeError):
            _send(admin)


def test_duplicate_within_window_is_refused(admin, two_members, sender_mock):
    _send(admin)
    _assert_refused(Code.Notification.BLAST_DUPLICATE, admin)
    sender_mock.assert_called_once()


def test_duplicate_after_window_allowed(admin, two_members, sender_mock):
    first = _send(admin)
    MemberEmailBlast.objects.filter(pk=first.pk).update(
        created_at=timezone.now() - timedelta(minutes=16)
    )
    _send(admin)
    assert sender_mock.call_count == 2


def test_concurrent_duplicate_is_refused(admin, two_members, sender_mock):
    MemberEmailBlast.objects.create(sender=admin, subject="s", body_html="<p>hi</p>")
    _assert_refused(Code.Notification.BLAST_DUPLICATE, admin)
    sender_mock.assert_not_called()


def test_no_recipients_raises(sender_mock):
    lone = make_user(membership_status=MembershipStatus.NONE, email="n@x.org")
    _assert_refused(Code.Notification.BLAST_NO_RECIPIENTS, lone)
    sender_mock.assert_not_called()


def test_send_test_requires_own_email(sender_mock):
    user = make_user(membership_status=MembershipStatus.ACTIVE_MEMBER, email="")
    with pytest.raises(ValidationException) as exc:
        send_test_blast(user=user, subject="s", body_html="<p>hi</p>")
    assert exc.value.code == Code.Notification.BLAST_NO_OWN_EMAIL
    assert exc.value.status_code == 400
    sender_mock.assert_not_called()


def test_send_test_sends_only_to_caller(admin, two_members, sender_mock):
    send_test_blast(user=admin, subject="s", body_html="<p>hi</p>")
    assert sender_mock.call_args.args[0] == ["admin@x.org"]
