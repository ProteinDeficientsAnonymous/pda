import pytest


@pytest.mark.django_db
class TestUserModel:
    def test_create_user_with_phone_number(self):
        from users.models import User

        user = User.objects.create_user(
            phone_number="+15550001001",
            password="testpass123",
            display_name="Test Member",
        )
        assert user.phone_number == "+15550001001"
        assert user.display_name == "Test Member"
        assert user.check_password("testpass123")

    def test_username_field_is_phone_number(self):
        from users.models import User

        assert User.USERNAME_FIELD == "phone_number"

    def test_user_has_no_first_last_name_fields(self):
        from users.models import User

        assert not hasattr(User, "first_name") or User.first_name is None
        assert not hasattr(User, "last_name") or User.last_name is None
        assert not hasattr(User, "username") or User.username is None

    def test_email_is_optional(self):
        from users.models import User

        user = User.objects.create_user(
            phone_number="+15550001002",
            password="testpass123",
        )
        assert user.email is None
        user.refresh_from_db()
        assert user.email is None

    def test_str_returns_display_name_or_phone(self):
        from users.models import User

        user = User.objects.create_user(
            phone_number="+15550001003",
            password="testpass123",
            display_name="Alex R",
        )
        assert str(user) == "Alex R"

        user_no_name = User.objects.create_user(
            phone_number="+15550001004",
            password="testpass123",
        )
        assert str(user_no_name) == "+15550001004"

    def test_create_superuser(self):
        from users.models import User

        user = User.objects.create_superuser(
            phone_number="+15550001005",
            password="adminpass123",
            display_name="Admin",
        )
        assert user.is_staff
        assert user.is_superuser
        assert user.phone_number == "+15550001005"

    def test_phone_number_is_required(self):
        from users.models import User

        with pytest.raises(ValueError, match="Phone number is required"):
            User.objects.create_user(phone_number="", password="testpass123")


@pytest.mark.django_db
class TestUserEmailField:
    def test_two_users_with_null_email_allowed(self):
        from users.models import User

        User.objects.create_user(phone_number="+12025550101", display_name="a", email=None)
        # Should NOT raise IntegrityError — multiple NULLs allowed.
        User.objects.create_user(phone_number="+12025550102", display_name="b", email=None)

    def test_duplicate_non_null_email_rejected(self):
        from django.db import IntegrityError
        from users.models import User

        User.objects.create_user(phone_number="+12025550101", display_name="a", email="dup@example.com")
        with pytest.raises(IntegrityError):
            User.objects.create_user(phone_number="+12025550102", display_name="b", email="dup@example.com")
