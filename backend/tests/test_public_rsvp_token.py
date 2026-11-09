from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from users.models import (
    PUBLIC_RSVP_TOKEN_MAX_LIFETIME_DAYS,
    PUBLIC_RSVP_TOKEN_TTL_DAYS,
    MembershipStatus,
    PublicRsvpToken,
    User,
)


@pytest.fixture
def public_rsvper(db):
    user = User.objects.create_user(
        phone_number="+12025559001",
        first_name="Non",
        last_name="Member",
        email="nonmember@example.com",
        membership_status=MembershipStatus.PUBLIC_RSVPER,
    )
    user.set_unusable_password()
    user.save(update_fields=["password"])
    return user


@pytest.mark.django_db
class TestIssue:
    def test_issue_produces_unique_urlsafe_token_with_90_day_expiry(self, public_rsvper):
        before = timezone.now()
        token = PublicRsvpToken.issue(public_rsvper)

        assert token.user_id == public_rsvper.id
        assert token.token
        # URL-safe: secrets.token_urlsafe yields only these characters.
        assert all(c.isalnum() or c in "-_" for c in token.token)
        assert token.revoked_at is None

        expected = before + timedelta(days=PUBLIC_RSVP_TOKEN_TTL_DAYS)
        # Expiry is ~90 days out; allow a small window for clock drift in the test.
        assert abs((token.expires_at - expected).total_seconds()) < 60

    def test_issue_tokens_are_unique(self, public_rsvper):
        first = PublicRsvpToken.issue(public_rsvper)
        second = PublicRsvpToken.issue(public_rsvper)
        assert first.token != second.token

    def test_issue_rejects_member(self, db):
        member = User.objects.create_user(
            phone_number="+12025559002",
            first_name="Member",
            membership_status=MembershipStatus.ACTIVE_MEMBER,
        )
        with pytest.raises(ValidationError):
            PublicRsvpToken.issue(member)


@pytest.mark.django_db
class TestIssueOrExtend:
    def test_first_call_issues_a_fresh_token(self, public_rsvper):
        token = PublicRsvpToken.issue_or_extend(public_rsvper)
        assert token.user_id == public_rsvper.id
        assert token.is_valid
        assert PublicRsvpToken.objects.filter(user=public_rsvper).count() == 1

    def test_extends_existing_valid_token_without_replacing_it(self, public_rsvper):
        first = PublicRsvpToken.issue(public_rsvper)
        # Pull expiry back so the extension is observable.
        first.expires_at = timezone.now() + timedelta(days=1)
        first.save(update_fields=["expires_at"])

        before = timezone.now()
        extended = PublicRsvpToken.issue_or_extend(public_rsvper)

        # Same row, same token string — a previously emailed link still resolves.
        assert extended.pk == first.pk
        assert extended.token == first.token
        assert PublicRsvpToken.objects.filter(user=public_rsvper).count() == 1

        expected = before + timedelta(days=PUBLIC_RSVP_TOKEN_TTL_DAYS)
        assert abs((extended.expires_at - expected).total_seconds()) < 60
        # The old URL still resolves after extension.
        assert PublicRsvpToken.resolve_user(first.token) == public_rsvper

    def test_issues_fresh_token_when_existing_is_expired(self, public_rsvper):
        stale = PublicRsvpToken.issue(public_rsvper)
        stale.expires_at = timezone.now() - timedelta(seconds=1)
        stale.save(update_fields=["expires_at"])

        fresh = PublicRsvpToken.issue_or_extend(public_rsvper)
        assert fresh.pk != stale.pk
        assert fresh.token != stale.token
        assert fresh.is_valid
        assert PublicRsvpToken.objects.filter(user=public_rsvper).count() == 2

    def test_issues_fresh_token_when_existing_is_revoked(self, public_rsvper):
        revoked = PublicRsvpToken.issue(public_rsvper)
        revoked.revoke()

        fresh = PublicRsvpToken.issue_or_extend(public_rsvper)
        assert fresh.pk != revoked.pk
        assert fresh.is_valid
        # The revoked token stays revoked.
        revoked.refresh_from_db()
        assert revoked.is_revoked

    def test_issues_fresh_token_when_existing_exceeds_max_lifetime(self, public_rsvper):
        old = PublicRsvpToken.issue(public_rsvper)
        # created_at is auto_now_add, so age it past the absolute cap via update().
        aged = timezone.now() - timedelta(days=PUBLIC_RSVP_TOKEN_MAX_LIFETIME_DAYS + 1)
        PublicRsvpToken.objects.filter(pk=old.pk).update(created_at=aged)

        fresh = PublicRsvpToken.issue_or_extend(public_rsvper)
        # Still valid (not expired/revoked) but too old to keep extending.
        assert fresh.pk != old.pk
        assert fresh.token != old.token
        assert PublicRsvpToken.objects.filter(user=public_rsvper).count() == 2

    def test_rejects_member(self, db):
        member = User.objects.create_user(
            phone_number="+12025559003",
            first_name="Member",
            membership_status=MembershipStatus.ACTIVE_MEMBER,
        )
        with pytest.raises(ValidationError):
            PublicRsvpToken.issue_or_extend(member)


@pytest.mark.django_db
class TestResolveUser:
    def test_valid_token_resolves_to_user(self, public_rsvper):
        token = PublicRsvpToken.issue(public_rsvper)
        assert PublicRsvpToken.resolve_user(token.token) == public_rsvper

    def test_unknown_token_returns_none(self, db):
        assert PublicRsvpToken.resolve_user("does-not-exist") is None

    def test_blank_token_returns_none(self, db):
        assert PublicRsvpToken.resolve_user("") is None

    def test_expired_token_returns_none(self, public_rsvper):
        token = PublicRsvpToken.issue(public_rsvper)
        token.expires_at = timezone.now() - timedelta(seconds=1)
        token.save(update_fields=["expires_at"])
        assert PublicRsvpToken.resolve_user(token.token) is None

    def test_revoked_token_returns_none(self, public_rsvper):
        token = PublicRsvpToken.issue(public_rsvper)
        token.revoke()
        assert PublicRsvpToken.resolve_user(token.token) is None


@pytest.mark.django_db
class TestRevoke:
    def test_revoke_stamps_revoked_at(self, public_rsvper):
        token = PublicRsvpToken.issue(public_rsvper)
        assert token.is_valid
        token.revoke()
        assert token.revoked_at is not None
        assert token.is_revoked
        assert not token.is_valid

    def test_revoke_is_idempotent(self, public_rsvper):
        token = PublicRsvpToken.issue(public_rsvper)
        token.revoke()
        first = token.revoked_at
        token.revoke()
        assert token.revoked_at == first
