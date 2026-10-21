from datetime import timedelta

import pytest
from community.models import (
    Event,
    EventSlugAlias,
    EventStatus,
    EventType,
    PageVisibility,
    event_lookup_q,
)
from django.utils import timezone


def _make_event(title: str) -> Event:
    return Event.objects.create(
        title=title,
        start_datetime=timezone.now() + timedelta(days=7),
        event_type=EventType.OFFICIAL,
        visibility=PageVisibility.PUBLIC,
        status=EventStatus.ACTIVE,
    )


@pytest.mark.django_db
class TestSlugAliasLookup:
    def test_alias_resolves_to_its_event(self, api_client):
        event = _make_event("Potluck")
        EventSlugAlias.objects.create(event=event, slug="old-potluck")
        resp = api_client.get("/api/community/events/old-potluck/")
        assert resp.status_code == 200
        assert resp.json()["slug"] == "potluck"

    def test_event_with_several_aliases_matches_once(self):
        event = _make_event("Potluck")
        EventSlugAlias.objects.create(event=event, slug="first")
        EventSlugAlias.objects.create(event=event, slug="second")
        for slug in ("potluck", "first", "second"):
            assert Event.objects.get(event_lookup_q(slug)).pk == event.pk


@pytest.mark.django_db
class TestGeneratedSlugAvoidsTakenNames:
    def test_skips_an_alias(self):
        event = _make_event("Picnic")
        EventSlugAlias.objects.create(event=event, slug="potluck")
        assert _make_event("Potluck").slug == "potluck-2"

    @pytest.mark.parametrize("title", ["Add", "Mine", "Manage"])
    def test_skips_reserved_route_names(self, title):
        assert _make_event(title).slug == f"{title.lower()}-2"
