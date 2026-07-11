import pytest
from users.models import User


@pytest.mark.django_db
class TestUserFullName:
    def test_full_name_combines_first_last(self):
        u = User.objects.create_user(
            phone_number="+15551230001", first_name="Ada", last_name="Lovelace"
        )
        assert u.full_name == "Ada Lovelace"

    def test_full_name_first_only(self):
        u = User.objects.create_user(phone_number="+15551230002", first_name="Cher")
        assert u.full_name == "Cher"

    def test_save_syncs_display_name(self):
        u = User.objects.create_user(
            phone_number="+15551230003", first_name="Ada", last_name="Lovelace"
        )
        u.refresh_from_db()
        assert u.display_name == "Ada Lovelace"

    def test_save_with_restricted_update_fields_still_syncs_display_name(self):
        u = User.objects.create_user(
            phone_number="+15551239500", first_name="Ada", last_name="Lovelace"
        )
        u.first_name = "Grace"
        u.last_name = "Hopper"
        u.save(update_fields=["first_name", "last_name"])
        u.refresh_from_db()
        assert u.display_name == "Grace Hopper"


@pytest.mark.django_db
class TestBackfillParsing:
    """The backfill logic (parse_display_name) applied to representative names."""

    def test_backfill_maps_existing_names(self):
        from users._name_parsing import parse_display_name

        u = User.objects.create_user(phone_number="+15551230100", first_name="x")
        u.first_name, u.last_name = parse_display_name("Grace Hopper")
        u.save()
        u.refresh_from_db()
        assert (u.first_name, u.last_name) == ("Grace", "Hopper")
        assert u.display_name == "Grace Hopper"


@pytest.mark.django_db
class TestJoinRequestNames:
    def test_join_request_full_name(self):
        from community.models.join_form import JoinRequest

        jr = JoinRequest.objects.create(
            first_name="Ada", last_name="Lovelace", phone_number="+15551239999"
        )
        assert jr.full_name == "Ada Lovelace"
