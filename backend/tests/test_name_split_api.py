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
