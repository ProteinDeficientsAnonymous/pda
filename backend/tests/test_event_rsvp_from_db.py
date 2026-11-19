"""EventRSVP.from_db must accept Django 6.1's fetch_mode argument."""

import warnings

import pytest
from community.models import Event, EventRSVP, RSVPStatus
from django.utils.deprecation import RemovedInDjango70Warning


@pytest.mark.django_db
def test_event_rsvp_from_db_accepts_fetch_mode(test_user):
    event = Event.objects.create(
        title="Test Event",
        start_datetime="2030-01-01T00:00:00Z",
        created_by=test_user,
    )
    created = EventRSVP.objects.create(event=event, user=test_user, status=RSVPStatus.ATTENDING)

    with warnings.catch_warnings():
        warnings.simplefilter("error", RemovedInDjango70Warning)
        loaded = EventRSVP.objects.get(pk=created.pk)

    assert loaded._loaded_status == RSVPStatus.ATTENDING
