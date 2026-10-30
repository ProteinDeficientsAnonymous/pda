from datetime import timedelta

import pytest
from community.models import Event
from django.utils import timezone
from users.permissions import PermissionKey

from tests._users import make_user


@pytest.fixture
def members(db):
    return [make_user(first_name=f"Member {i}") for i in range(1, 5)]


@pytest.fixture
def host(db):
    return make_user(first_name="Host")


@pytest.fixture
def cohost(db):
    return make_user(first_name="Co-host")


@pytest.fixture
def admin_user(db):
    return make_user(PermissionKey.MANAGE_EVENTS, first_name="Event", last_name="Admin")


@pytest.fixture
def stats_event(db, host, cohost, members):
    event = Event.objects.create(
        title="Stats Event",
        start_datetime=timezone.now() + timedelta(days=7),
        end_datetime=timezone.now() + timedelta(days=7, hours=2),
        rsvp_enabled=True,
        created_by=host,
    )
    event.co_hosts.add(cohost)
    event.invited_users.set(members)
    return event


@pytest.fixture
def open_check_in_event(db, host, cohost, members):
    """Event starting in 30 min — check-in window is open."""
    event = Event.objects.create(
        title="Check-in Open Event",
        start_datetime=timezone.now() + timedelta(minutes=30),
        end_datetime=timezone.now() + timedelta(hours=2),
        rsvp_enabled=True,
        created_by=host,
    )
    event.co_hosts.add(cohost)
    event.invited_users.set(members)
    return event
