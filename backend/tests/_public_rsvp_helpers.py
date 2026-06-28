"""Shared helpers for the public-RSVP endpoint tests.

POST /api/community/public/events/{event_id}/rsvp/ — split across
test_public_rsvp.py (submission/dedup/gating/validation) and
test_public_rsvp_capacity.py (capacity/waitlist/robustness) to stay under the
per-file line limit. The common request builders and factories live here.
"""

from community.models import (
    Event,
    EventStatus,
    EventType,
    PageVisibility,
    RSVPStatus,
)
from users.models import User

from tests.conftest import future_iso

URL_TEMPLATE = "/api/community/public/events/{event_id}/rsvp/"


def url(event):
    return URL_TEMPLATE.format(event_id=event.id)


def payload(**overrides):
    base = {
        "name": "Sam Green",
        "email": "sam@example.com",
        "phone_number": "+14155550123",
        "status": RSVPStatus.ATTENDING,
        "has_plus_one": False,
    }
    base.update(overrides)
    return base


def post(api_client, event, **overrides):
    return api_client.post(url(event), payload(**overrides), content_type="application/json")


def first_code(response) -> str:
    return response.json()["detail"][0]["code"]


def make_official_event(**overrides):
    base = {
        "title": "Official Public Event",
        "start_datetime": future_iso(days=30),
        "event_type": EventType.OFFICIAL,
        "visibility": PageVisibility.PUBLIC,
        "status": EventStatus.ACTIVE,
        "rsvp_enabled": True,
    }
    base.update(overrides)
    return Event.objects.create(**base)


def make_non_member(phone, email, name="Existing Nonmember"):
    user = User.objects.create_user(
        phone_number=phone,
        display_name=name,
        email=email,
        is_member=False,
    )
    user.set_unusable_password()
    user.save(update_fields=["password"])
    return user
