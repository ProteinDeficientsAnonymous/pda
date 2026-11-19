from datetime import timedelta

import pytest
from community.join_requests.approval import provision_tentative_user
from community.models import (
    AttendanceStatus,
    Event,
    EventRSVP,
    EventType,
    JoinRequestStatus,
    RSVPStatus,
)
from django.utils import timezone
from users.models import User

from tests._auth import auth_headers_for


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

    provision_tentative_user(join_request, vettor)
    join_request.status = JoinRequestStatus.TENTATIVE
    join_request.save(update_fields=["status"])
    join_request.refresh_from_db()
    EventRSVP.objects.create(event=event, user=join_request.user, status=RSVPStatus.ATTENDING)
    return join_request.user


def decide(api_client, headers, join_request, status):
    return api_client.patch(
        f"/api/community/join-requests/{join_request.id}/",
        {"status": status},
        content_type="application/json",
        **headers,
    )


def check_in(api_client, event, user):
    return api_client.post(
        f"/api/community/events/{event.id}/rsvps/{user.pk}/attendance/",
        {"attendance": AttendanceStatus.ATTENDED},
        content_type="application/json",
        **auth_headers_for(event.created_by),
    )
