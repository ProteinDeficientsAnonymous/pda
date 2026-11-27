import pytest
from django.conf import settings
from notifications.member_blasts.service import clean_body, collect_recipients, render_blast
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
