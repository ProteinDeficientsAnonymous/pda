from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from users.models import (
    NON_MEMBER_RSVP_TOKEN_MAX_LIFETIME_DAYS,
    NON_MEMBER_RSVP_TOKEN_TTL_DAYS,
    NonMemberRsvpToken,
    User,
)


@pytest.fixture
def non_member(db):
    user = User.objects.create_user(
        phone_number="+12025559001",
        first_name="Non",
        last_name="Member",
        email="nonmember@example.com",
        is_member=False,
    )
    user.set_unusable_password()
    user.save(update_fields=["password"])
    return user


@pytest.mark.django_db
class TestIssue:
    def test_issue_produces_unique_urlsafe_token_with_90_day_expiry(self, non_member):
        before = timezone.now()
        token = NonMemberRsvpToken.issue(non_member)

        assert token.user_id == non_member.id
        assert token.token
        # URL-safe: secrets.token_urlsafe yields only these characters.
        assert all(c.isalnum() or c in "-_" for c in token.token)
        assert token.revoked_at is None

        expected = before + timedelta(days=NON_MEMBER_RSVP_TOKEN_TTL_DAYS)
        # Expiry is ~90 days out; allow a small window for clock drift in the test.
        assert abs((token.expires_at - expected).total_seconds()) < 60

    def test_issue_tokens_are_unique(self, non_member):
        first = NonMemberRsvpToken.issue(non_member)
        second = NonMemberRsvpToken.issue(non_member)
        assert first.token != second.token

    def test_issue_rejects_member(self, db):
        member = User.objects.create_user(
            phone_number="+12025559002",
            first_name="Member",
            is_member=True,
        )
        with pytest.raises(ValidationError):
            NonMemberRsvpToken.issue(member)


@pytest.mark.django_db
class TestIssueOrExtend:
    def test_first_call_issues_a_fresh_token(self, non_member):
        token = NonMemberRsvpToken.issue_or_extend(non_member)
        assert token.user_id == non_member.id
        assert token.is_valid
        assert NonMemberRsvpToken.objects.filter(user=non_member).count() == 1

    def test_extends_existing_valid_token_without_replacing_it(self, non_member):
        first = NonMemberRsvpToken.issue(non_member)
        # Pull expiry back so the extension is observable.
        first.expires_at = timezone.now() + timedelta(days=1)
        first.save(update_fields=["expires_at"])

        before = timezone.now()
        extended = NonMemberRsvpToken.issue_or_extend(non_member)

        # Same row, same token string — a previously emailed link still resolves.
        assert extended.pk == first.pk
        assert extended.token == first.token
        assert NonMemberRsvpToken.objects.filter(user=non_member).count() == 1

        expected = before + timedelta(days=NON_MEMBER_RSVP_TOKEN_TTL_DAYS)
        assert abs((extended.expires_at - expected).total_seconds()) < 60
        # The old URL still resolves after extension.
        assert NonMemberRsvpToken.resolve_user(first.token) == non_member

    def test_issues_fresh_token_when_existing_is_expired(self, non_member):
        stale = NonMemberRsvpToken.issue(non_member)
        stale.expires_at = timezone.now() - timedelta(seconds=1)
        stale.save(update_fields=["expires_at"])

        fresh = NonMemberRsvpToken.issue_or_extend(non_member)
        assert fresh.pk != stale.pk
        assert fresh.token != stale.token
        assert fresh.is_valid
        assert NonMemberRsvpToken.objects.filter(user=non_member).count() == 2

    def test_issues_fresh_token_when_existing_is_revoked(self, non_member):
        revoked = NonMemberRsvpToken.issue(non_member)
        revoked.revoke()

        fresh = NonMemberRsvpToken.issue_or_extend(non_member)
        assert fresh.pk != revoked.pk
        assert fresh.is_valid
        # The revoked token stays revoked.
        revoked.refresh_from_db()
        assert revoked.is_revoked

    def test_issues_fresh_token_when_existing_exceeds_max_lifetime(self, non_member):
        old = NonMemberRsvpToken.issue(non_member)
        # created_at is auto_now_add, so age it past the absolute cap via update().
        aged = timezone.now() - timedelta(days=NON_MEMBER_RSVP_TOKEN_MAX_LIFETIME_DAYS + 1)
        NonMemberRsvpToken.objects.filter(pk=old.pk).update(created_at=aged)

        fresh = NonMemberRsvpToken.issue_or_extend(non_member)
        # Still valid (not expired/revoked) but too old to keep extending.
        assert fresh.pk != old.pk
        assert fresh.token != old.token
        assert NonMemberRsvpToken.objects.filter(user=non_member).count() == 2

    def test_rejects_member(self, db):
        member = User.objects.create_user(
            phone_number="+12025559003",
            first_name="Member",
            is_member=True,
        )
        with pytest.raises(ValidationError):
            NonMemberRsvpToken.issue_or_extend(member)


@pytest.mark.django_db
class TestResolveUser:
    def test_valid_token_resolves_to_user(self, non_member):
        token = NonMemberRsvpToken.issue(non_member)
        assert NonMemberRsvpToken.resolve_user(token.token) == non_member

    def test_unknown_token_returns_none(self, db):
        assert NonMemberRsvpToken.resolve_user("does-not-exist") is None

    def test_blank_token_returns_none(self, db):
        assert NonMemberRsvpToken.resolve_user("") is None

    def test_expired_token_returns_none(self, non_member):
        token = NonMemberRsvpToken.issue(non_member)
        token.expires_at = timezone.now() - timedelta(seconds=1)
        token.save(update_fields=["expires_at"])
        assert NonMemberRsvpToken.resolve_user(token.token) is None

    def test_revoked_token_returns_none(self, non_member):
        token = NonMemberRsvpToken.issue(non_member)
        token.revoke()
        assert NonMemberRsvpToken.resolve_user(token.token) is None


@pytest.mark.django_db
class TestRevoke:
    def test_revoke_stamps_revoked_at(self, non_member):
        token = NonMemberRsvpToken.issue(non_member)
        assert token.is_valid
        token.revoke()
        assert token.revoked_at is not None
        assert token.is_revoked
        assert not token.is_valid

    def test_revoke_is_idempotent(self, non_member):
        token = NonMemberRsvpToken.issue(non_member)
        token.revoke()
        first = token.revoked_at
        token.revoke()
        assert token.revoked_at == first
