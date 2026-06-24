"""Tests for User.is_member, the members() manager, and the email partial-unique index."""

import pytest
from django.db import IntegrityError, transaction


@pytest.mark.django_db
class TestMembersManager:
    def test_is_member_field_defaults_to_false(self):
        """The model default is False — accounts must be explicitly promoted.

        (The conftest create_user monkeypatch forces is_member=True for the
        general test population, so assert the raw field default directly.)
        """
        from users.models import User

        assert User._meta.get_field("is_member").default is False
        assert User(phone_number="+12025550201").is_member is False

    def test_members_returns_only_members(self):
        from users.models import User

        member = User.objects.create_user(phone_number="+12025550202", password="x")
        non_member = User.objects.create_user(phone_number="+12025550203", is_member=False)

        member_ids = set(User.objects.members().values_list("pk", flat=True))
        assert member.pk in member_ids
        assert non_member.pk not in member_ids

    def test_default_manager_returns_both(self):
        from users.models import User

        member = User.objects.create_user(phone_number="+12025550204", password="x")
        non_member = User.objects.create_user(phone_number="+12025550205", is_member=False)

        all_ids = set(User.objects.values_list("pk", flat=True))
        assert {member.pk, non_member.pk} <= all_ids

    def test_members_is_chainable(self):
        from users.models import User

        member = User.objects.create_user(phone_number="+12025550206", password="x")
        User.objects.create_user(phone_number="+12025550207", is_member=False)

        qs = User.objects.members().filter(phone_number="+12025550206")
        assert list(qs.values_list("pk", flat=True)) == [member.pk]


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
        from importlib import import_module

        module = import_module("users.migrations.0028_user_is_member_email_partial_unique")
        return module.Migration.operations

    def test_field_added_with_default_true_for_backfill(self):
        from django.db.migrations import AddField

        add = next(
            op
            for op in self._load_operations()
            if isinstance(op, AddField) and op.name == "is_member"
        )
        # default=True at AddField time → every pre-existing row backfills to member.
        assert add.field.default is True

    def test_field_default_flipped_to_false_for_new_rows(self):
        from django.db.migrations import AlterField

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
        from users.models import User

        User.objects.create_user(phone_number="+12025550209", password="x", email=None)
        User.objects.create_user(phone_number="+12025550210", password="x", email=None)
        assert User.objects.filter(email__isnull=True).count() == 2

    def test_allows_multiple_blank_emails(self):
        from users.models import User

        User.objects.create_user(phone_number="+12025550211", password="x", email="")
        User.objects.create_user(phone_number="+12025550212", password="x", email="")
        assert User.objects.filter(email="").count() == 2

    def test_rejects_duplicate_non_blank_email(self):
        from users.models import User

        User.objects.create_user(
            phone_number="+12025550213", password="x", email="dupe@example.com"
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(
                    phone_number="+12025550214", password="x", email="dupe@example.com"
                )

    def test_rejects_duplicate_email_across_member_and_non_member(self):
        from users.models import User

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
