"""Slug generation, collision dedupe, and slug/uuid resolution on the event detail route."""

from datetime import timedelta

import pytest
from community.models import Event, EventStatus, EventType, PageVisibility, event_lookup_q
from django.utils import timezone


def _make_event(title: str, **kwargs) -> Event:
    return Event.objects.create(
        title=title,
        start_datetime=timezone.now() + timedelta(days=7),
        event_type=EventType.OFFICIAL,
        visibility=PageVisibility.PUBLIC,
        status=EventStatus.ACTIVE,
        **kwargs,
    )


@pytest.mark.django_db
class TestSlugGeneration:
    def test_slug_derived_from_title(self):
        assert _make_event("Potluck in the Park").slug == "potluck-in-the-park"

    def test_punctuation_and_case_normalized(self):
        assert _make_event("Vegan BRUNCH: Round #2!").slug == "vegan-brunch-round-2"

    def test_untitleable_title_falls_back(self):
        assert _make_event("!!!").slug == "event"

    def test_long_title_truncated_to_fit_field(self):
        event = _make_event("a potluck " * 30)
        assert len(event.slug) <= 80

    def test_explicit_slug_is_respected(self):
        assert _make_event("Potluck in the Park", slug="custom-slug").slug == "custom-slug"


@pytest.mark.django_db
class TestSlugCollisions:
    def test_duplicate_titles_get_numeric_suffixes(self):
        slugs = [_make_event("Weekly Potluck").slug for _ in range(3)]
        assert slugs == ["weekly-potluck", "weekly-potluck-2", "weekly-potluck-3"]

    def test_suffix_fills_gap_after_delete(self):
        _make_event("Weekly Potluck")
        second = _make_event("Weekly Potluck")
        assert second.slug == "weekly-potluck-2"
        second.delete()
        assert _make_event("Weekly Potluck").slug == "weekly-potluck-2"

    def test_slug_is_stable_when_title_changes(self):
        event = _make_event("Original Title")
        event.title = "A Completely Different Title"
        event.save()
        event.refresh_from_db()
        assert event.slug == "original-title"

    def test_title_prefix_does_not_steal_another_slug(self):
        _make_event("Potluck")
        # "potluck-2" already exists as a real title, so the dedupe must skip past it.
        _make_event("Potluck 2")
        assert _make_event("Potluck").slug == "potluck-3"


@pytest.mark.django_db
class TestEventLookupQ:
    def test_uuid_matches_by_id(self):
        event = _make_event("Potluck in the Park")
        assert Event.objects.get(event_lookup_q(str(event.id))).pk == event.pk

    def test_slug_matches_by_slug(self):
        event = _make_event("Potluck in the Park")
        assert Event.objects.get(event_lookup_q(event.slug)).pk == event.pk


@pytest.mark.django_db
class TestEventDetailRoute:
    def test_resolves_by_slug(self, api_client):
        event = _make_event("Potluck in the Park")
        response = api_client.get(f"/api/community/events/{event.slug}/")
        assert response.status_code == 200
        assert response.json()["id"] == str(event.id)

    def test_uuid_url_still_resolves(self, api_client):
        event = _make_event("Potluck in the Park")
        response = api_client.get(f"/api/community/events/{event.id}/")
        assert response.status_code == 200
        assert response.json()["id"] == str(event.id)

    def test_both_forms_return_the_same_payload(self, api_client):
        event = _make_event("Potluck in the Park")
        by_slug = api_client.get(f"/api/community/events/{event.slug}/")
        by_uuid = api_client.get(f"/api/community/events/{event.id}/")
        assert by_slug.json() == by_uuid.json()

    def test_detail_exposes_slug(self, api_client):
        event = _make_event("Potluck in the Park")
        response = api_client.get(f"/api/community/events/{event.id}/")
        assert response.json()["slug"] == "potluck-in-the-park"

    def test_unknown_slug_404s(self, api_client):
        response = api_client.get("/api/community/events/no-such-event/")
        assert response.status_code == 404
