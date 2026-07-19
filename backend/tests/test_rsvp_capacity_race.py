import threading

import pytest
from community.models import Event, EventRSVP, RSVPStatus
from django import db
from django.test import Client
from ninja_jwt.tokens import RefreshToken
from users.models import User

from tests.conftest import future_iso


def _make_user(i):
    return User.objects.create_user(
        phone_number=f"+1415555{9100 + i}",
        password="Testpass123!",
        first_name=f"Racer{i}",
        last_name="",
    )


def _jwt_headers(user):
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.mark.django_db(transaction=True)
class TestRsvpCapacityRace:
    def test_concurrent_rsvps_never_exceed_capacity(self, test_user):
        """N threads RSVP to a 1-seat event at once; select_for_update() on the
        Event row must serialize them so exactly 1 lands attending, the rest
        waitlisted — never an overbooked headcount (issue #945)."""
        event = Event.objects.create(
            title="Race Event",
            start_datetime=future_iso(days=30),
            rsvp_enabled=True,
            max_attendees=1,
            created_by=test_user,
        )
        thread_count = 8
        users = [_make_user(i) for i in range(thread_count)]
        results = [None] * thread_count

        def rsvp(i):
            try:
                client = Client()
                resp = client.post(
                    f"/api/community/events/{event.id}/rsvp/",
                    {"status": RSVPStatus.ATTENDING, "has_plus_one": False},
                    content_type="application/json",
                    **_jwt_headers(users[i]),
                )
                results[i] = resp.status_code
            finally:
                db.connections.close_all()

        threads = [threading.Thread(target=rsvp, args=(i,)) for i in range(thread_count)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(code == 200 for code in results), results

        attending = EventRSVP.objects.filter(event=event, status=RSVPStatus.ATTENDING).count()
        waitlisted = EventRSVP.objects.filter(event=event, status=RSVPStatus.WAITLISTED).count()
        assert attending == 1
        assert waitlisted == thread_count - 1
