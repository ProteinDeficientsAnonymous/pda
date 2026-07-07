import pytest
from community._validation import ValidationException
from django.db import IntegrityError
from users._helpers import _check_and_set_email, _normalize_email
from users.models import User


@pytest.mark.django_db
class TestUserModel:
    def test_create_user_with_phone_number(self):
        user = User.objects.create_user(
            phone_number="+15550001001",
            password="testpass123",
            display_name="Test Member",
        )
        assert user.phone_number == "+15550001001"
        assert user.display_name == "Test Member"
        assert user.check_password("testpass123")

    def test_username_field_is_phone_number(self):
        assert User.USERNAME_FIELD == "phone_number"

    def test_user_has_no_first_last_name_fields(self):
        assert not hasattr(User, "first_name") or User.first_name is None
        assert not hasattr(User, "last_name") or User.last_name is None
        assert not hasattr(User, "username") or User.username is None

    def test_email_is_optional(self):
        user = User.objects.create_user(
            phone_number="+15550001002",
            password="testpass123",
        )
        assert user.email is None
        user.refresh_from_db()
        assert user.email is None

    def test_str_returns_display_name_or_phone(self):
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
        user = User.objects.create_superuser(
            phone_number="+15550001005",
            password="adminpass123",
            display_name="Admin",
        )
        assert user.is_staff
        assert user.is_superuser
        assert user.phone_number == "+15550001005"

    def test_phone_number_is_required(self):
        with pytest.raises(ValueError, match="Phone number is required"):
            User.objects.create_user(phone_number="", password="testpass123")


@pytest.mark.django_db
class TestUserEmailField:
    def test_two_users_with_null_email_allowed(self):
        User.objects.create_user(phone_number="+12025550101", display_name="a", email=None)
        # Should NOT raise IntegrityError — multiple NULLs allowed.
        User.objects.create_user(phone_number="+12025550102", display_name="b", email=None)

    def test_duplicate_non_null_email_rejected(self):
        User.objects.create_user(
            phone_number="+12025550101", display_name="a", email="dup@example.com"
        )
        with pytest.raises(IntegrityError):
            User.objects.create_user(
                phone_number="+12025550102", display_name="b", email="dup@example.com"
            )


@pytest.mark.django_db
class TestCheckAndSetEmail:
    def test_assigns_normalized(self):
        u = User(phone_number="+12025550101", display_name="a")
        _check_and_set_email(u, "Foo@Example.COM")
        assert u.email == "foo@example.com"

    def test_blank_assigns_none(self):
        u = User(phone_number="+12025550101", display_name="a")
        _check_and_set_email(u, "  ")
        assert u.email is None

    def test_raises_on_collision(self):
        User.objects.create_user(
            phone_number="+12025550199", display_name="other", email="taken@example.com"
        )
        target = User(phone_number="+12025550101", display_name="a")
        with pytest.raises(ValidationException):
            _check_and_set_email(target, "Taken@Example.com")

    def test_exclude_pk_allows_self_update(self):
        existing = User.objects.create_user(
            phone_number="+12025550101", display_name="a", email="me@example.com"
        )
        # Should not raise — same user re-submitting their own email
        _check_and_set_email(existing, "Me@Example.com", exclude_pk=existing.pk)
        assert existing.email == "me@example.com"


class TestNormalizeEmail:
    def test_lowercases(self):
        assert _normalize_email("Foo@Example.COM") == "foo@example.com"

    def test_strips_whitespace(self):
        assert _normalize_email("  foo@example.com  ") == "foo@example.com"

    def test_blank_returns_none(self):
        assert _normalize_email("") is None
        assert _normalize_email("   ") is None
        assert _normalize_email(None) is None
