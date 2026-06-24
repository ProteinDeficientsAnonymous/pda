"""Tests for User.is_member, the members() manager, and the email partial-unique index."""

import pytest
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db
class TestMembersManager:
    def test_create_user_defaults_to_member(self):
        from users.models import User

        user = User.objects.create_user(phone_number="+12025550201", password="x")
        assert user.is_member is True

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


@pytest.mark.django_db(transaction=True)
class TestMembersBackfillMigration:
    """Exercise the real migration: a row that exists before is_member is added
    must be backfilled to is_member=True when 0028 runs."""

    def test_existing_row_is_backfilled_to_member(self):
        executor = MigrationExecutor(connection)
        app = "users"
        before = "0027_user_sms_consent_at"
        after = "0028_user_is_member_email_partial_unique"

        # Rewind to before is_member existed, then insert a row at that state.
        executor.migrate([(app, before)])
        executor.loader.build_graph()
        OldUser = executor.loader.project_state([(app, before)]).apps.get_model(app, "User")
        row = OldUser.objects.create(phone_number="+12025550290", password="x")
        assert not hasattr(row, "is_member")

        # Apply 0028 and confirm the pre-existing row was backfilled.
        executor = MigrationExecutor(connection)
        executor.migrate([(app, after)])
        NewUser = executor.loader.project_state([(app, after)]).apps.get_model(app, "User")
        assert NewUser.objects.get(pk=row.pk).is_member is True

    def teardown_method(self):
        # Leave the DB at the latest migration for the rest of the suite.
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())


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
