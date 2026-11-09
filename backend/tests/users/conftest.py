import pytest
from users.models import MembershipStatus, User


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
    """A member User. Reusable across user test files."""
    return User.objects.create_user(
        phone_number="+12025550401",
        password="memberpass123",
        first_name="Member",
        last_name="User",
    )


@pytest.fixture
def non_member(db):
    """A public rsvper; overrides the conftest create_user default of member."""
    return User.objects.create_user(
        phone_number="+12025550402",
        first_name="Non-member",
        last_name="User",
        membership_status=MembershipStatus.PUBLIC_RSVPER,
    )
