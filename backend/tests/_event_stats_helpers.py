from datetime import timedelta

import pytest
from community.models import Event
from django.utils import timezone
from users.models import Role, User
from users.permissions import PermissionKey


@pytest.fixture
def members(db):
    return [
        User.objects.create_user(
            phone_number=f"+1202555090{i}",
            password="x",
            first_name=f"Member {i}",
        )
        for i in range(1, 5)
    ]


@pytest.fixture
def host_user(db):
    return User.objects.create_user(
        phone_number="+12025558000",
        password="x",
        first_name="Host",
    )


@pytest.fixture
def cohost_user(db):
    return User.objects.create_user(
        phone_number="+12025558001",
        password="x",
        first_name="Co-host",
    )


@pytest.fixture
def admin_user(db):
    admin = User.objects.create_user(
        phone_number="+12025558002",
        password="x",
        first_name="Event",
        last_name="Admin",
    )
    role = Role.objects.create(name="stats_admin", permissions=[PermissionKey.MANAGE_EVENTS])
    admin.roles.add(role)
    return admin


@pytest.fixture
def stats_event(db, host_user, cohost_user, members):
    event = Event.objects.create(
        title="Stats Event",
        start_datetime=timezone.now() + timedelta(days=7),
        end_datetime=timezone.now() + timedelta(days=7, hours=2),
        rsvp_enabled=True,
        created_by=host_user,
    )
    event.co_hosts.add(cohost_user)
    event.invited_users.set(members)
    return event


@pytest.fixture
def open_check_in_event(db, host_user, cohost_user, members):
    """Event starting in 30 min — check-in window is open."""
    event = Event.objects.create(
        title="Check-in Open Event",
        start_datetime=timezone.now() + timedelta(minutes=30),
        end_datetime=timezone.now() + timedelta(hours=2),
        rsvp_enabled=True,
        created_by=host_user,
    )
    event.co_hosts.add(cohost_user)
    event.invited_users.set(members)
    return event
