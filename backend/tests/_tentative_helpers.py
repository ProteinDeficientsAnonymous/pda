from datetime import timedelta

import pytest
from community._join_request_approval import _provision_tentative_user
from community.models import Event, EventRSVP, EventType, JoinRequestStatus, RSVPStatus
from django.utils import timezone
from users.models import User


@pytest.fixture
def open_official_event(db):
    host = User.objects.create_user(phone_number="+12025557000", first_name="Host")
    return Event.objects.create(
        title="Official Meetup",
        start_datetime=timezone.now() + timedelta(minutes=30),
        end_datetime=timezone.now() + timedelta(hours=2),
        rsvp_enabled=True,
        event_type=EventType.OFFICIAL,
        created_by=host,
    )


def tentative_user_with_rsvp(join_request, event, vettor):

    _provision_tentative_user(join_request, vettor)
    join_request.status = JoinRequestStatus.TENTATIVE
    join_request.save(update_fields=["status"])
    join_request.refresh_from_db()
    EventRSVP.objects.create(event=event, user=join_request.user, status=RSVPStatus.ATTENDING)
    return join_request.user
