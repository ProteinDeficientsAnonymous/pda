import pytest
from users.models import User


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        phone_number="+12025550301",
        password="otherpass123",
        first_name="Other",
        last_name="User",
    )


@pytest.fixture
def member(db):
    """A member User (is_member=True). Reusable across user test files."""
    return User.objects.create_user(
        phone_number="+12025550401",
        password="memberpass123",
        first_name="Member",
        last_name="User",
    )


@pytest.fixture
def non_member(db):
    """A non-member User (is_member=False) — e.g. a public-RSVP account.

    Passes is_member=False explicitly to override the conftest create_user
    monkeypatch, which otherwise forces is_member=True for the test population.
    """
    return User.objects.create_user(
        phone_number="+12025550402",
        first_name="Non-member",
        last_name="User",
        is_member=False,
    )
