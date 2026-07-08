"""Tests for User.is_member, the members() manager, and the email partial-unique index."""

from importlib import import_module

import pytest
from django.db import IntegrityError, transaction
from django.db.migrations import AddField, AlterField
from django.utils import timezone
from users.models import User


@pytest.mark.django_db
class TestMembersManager:
    def test_is_member_field_defaults_to_false(self):
        """The model default is False — accounts must be explicitly promoted.

        (The conftest create_user monkeypatch forces is_member=True for the
        general test population, so assert the raw field default directly.)
        """
        assert User._meta.get_field("is_member").default is False
        assert User(phone_number="+12025550201").is_member is False

    def test_members_returns_only_members(self, member, non_member):
        member_ids = set(User.objects.members().values_list("pk", flat=True))
        assert member.pk in member_ids
        assert non_member.pk not in member_ids

    def test_default_manager_returns_both(self, member, non_member):
        all_ids = set(User.objects.values_list("pk", flat=True))
        assert {member.pk, non_member.pk} <= all_ids

    def test_members_is_chainable(self, member, non_member):
        qs = User.objects.members().filter(phone_number=member.phone_number)
        assert list(qs.values_list("pk", flat=True)) == [member.pk]


@pytest.mark.django_db
class TestActiveMembersManager:
    """active_members() bundles the full member-visibility predicate."""

    def _active_member_ids(self):
        return set(User.objects.active_members().values_list("pk", flat=True))

    def test_includes_plain_member(self, member):
        assert member.pk in self._active_member_ids()

    def test_excludes_non_member(self, non_member):
        assert non_member.pk not in self._active_member_ids()

    def test_excludes_paused_member(self, member):
        member.is_paused = True
        member.save(update_fields=["is_paused"])
        assert member.pk not in self._active_member_ids()

    def test_excludes_archived_member(self, member):
        member.archived_at = timezone.now()
        member.save(update_fields=["archived_at"])
        assert member.pk not in self._active_member_ids()

    def test_excludes_inactive_member(self, member):
        """is_active is Django's built-in flag, kept as defense-in-depth."""
        member.is_active = False
        member.save(update_fields=["is_active"])
        assert member.pk not in self._active_member_ids()

    def test_includes_onboarding_pending_member(self, member):
        """needs_onboarding is NOT part of the base predicate — only the directory
        excludes it. profile/search surfaces still see onboarding-pending members.
        """
        member.needs_onboarding = True
        member.save(update_fields=["needs_onboarding"])
        assert member.pk in self._active_member_ids()

    def test_is_chainable(self, member):
        member.needs_onboarding = True
        member.save(update_fields=["needs_onboarding"])
        qs = User.objects.active_members().filter(needs_onboarding=False)
        assert member.pk not in set(qs.values_list("pk", flat=True))


class TestMembersBackfillMigration:
    """Assert migration 0028 adds is_member so existing rows backfill to member
    while new rows default to non-member.

    The operations are inspected directly rather than replayed against the live
    test DB: a real rewind/replay mutates the shared --reuse-db database that
    sibling xdist workers depend on, which poisons unrelated tests. The two
    AddField/AlterField operations fully determine the runtime behavior — add
    with default=True (Django backfills every existing row to True), then alter
    the field default to False (future rows are non-members).
    """

    def _load_operations(self):
        module = import_module("users.migrations.0028_user_is_member_email_partial_unique")
        return module.Migration.operations

    def test_field_added_with_default_true_for_backfill(self):
        add = next(
            op
            for op in self._load_operations()
            if isinstance(op, AddField) and op.name == "is_member"
        )
        # default=True at AddField time → every pre-existing row backfills to member.
        assert add.field.default is True

    def test_field_default_flipped_to_false_for_new_rows(self):
        alter = next(
            op
            for op in self._load_operations()
            if isinstance(op, AlterField) and op.name == "is_member"
        )
        # AlterField flips the default so new (public-RSVP) rows are non-members.
        assert alter.field.default is False


@pytest.mark.django_db
class TestEmailPartialUniqueIndex:
    def test_allows_multiple_null_emails(self):
        User.objects.create_user(phone_number="+12025550209", password="x", email=None)
        User.objects.create_user(phone_number="+12025550210", password="x", email=None)
        assert User.objects.filter(email__isnull=True).count() == 2

    def test_allows_multiple_blank_emails(self):
        User.objects.create_user(phone_number="+12025550211", password="x", email="")
        User.objects.create_user(phone_number="+12025550212", password="x", email="")
        assert User.objects.filter(email="").count() == 2

    def test_rejects_duplicate_non_blank_email(self):
        User.objects.create_user(
            phone_number="+12025550213", password="x", email="dupe@example.com"
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(
                    phone_number="+12025550214", password="x", email="dupe@example.com"
                )

    def test_rejects_duplicate_email_across_member_and_non_member(self):
        User.objects.create_user(
            phone_number="+12025550215", password="x", email="shared@example.com"
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(
                    phone_number="+12025550216",
                    is_member=False,
                    email="shared@example.com",
                )
