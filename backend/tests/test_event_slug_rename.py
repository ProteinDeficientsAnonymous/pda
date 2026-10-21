import json
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
from ninja_jwt.tokens import RefreshToken
from users.models import User


def _make_user(phone: str, name: str) -> User:
    return User.objects.create_user(phone_number=phone, password="testpass123", first_name=name)


def _auth_headers(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


def _make_event(title: str, created_by: User | None = None) -> Event:
    return Event.objects.create(
        title=title,
        start_datetime=timezone.now() + timedelta(days=7),
        event_type=EventType.COMMUNITY,
        visibility=PageVisibility.PUBLIC,
        status=EventStatus.ACTIVE,
        created_by=created_by,
    )


def _patch_slug(api_client, event: Event, slug: str, user: User):
    return api_client.patch(
        f"/api/community/events/{event.id}/",
        data=json.dumps({"slug": slug}),
        content_type="application/json",
        **_auth_headers(user),
    )


@pytest.fixture
def host(db) -> User:
    return _make_user("+12025550301", "Host")


@pytest.fixture
def cohost(db) -> User:
    return _make_user("+12025550302", "CoHost")


@pytest.fixture
def stranger(db) -> User:
    return _make_user("+12025550303", "Stranger")


@pytest.mark.django_db
class TestHostRenamesSlug:
    def test_creator_can_rename(self, api_client, host):
        event = _make_event("Potluck in the Park", created_by=host)
        resp = _patch_slug(api_client, event, "summer-potluck", host)
        assert resp.status_code == 200
        assert resp.json()["slug"] == "summer-potluck"
        event.refresh_from_db()
        assert event.slug == "summer-potluck"

    def test_cohost_can_rename(self, api_client, host, cohost):
        event = _make_event("Potluck in the Park", created_by=host)
        event.co_hosts.add(cohost)
        resp = _patch_slug(api_client, event, "summer-potluck", cohost)
        assert resp.status_code == 200
        assert resp.json()["slug"] == "summer-potluck"

    def test_non_host_cannot_rename(self, api_client, host, stranger):
        event = _make_event("Potluck in the Park", created_by=host)
        resp = _patch_slug(api_client, event, "hijacked", stranger)
        assert resp.status_code == 403
        event.refresh_from_db()
        assert event.slug == "potluck-in-the-park"

    def test_input_is_trimmed_and_lowercased(self, api_client, host):
        event = _make_event("Potluck", created_by=host)
        resp = _patch_slug(api_client, event, "  Summer-Potluck ", host)
        assert resp.status_code == 200
        assert resp.json()["slug"] == "summer-potluck"

    def test_unchanged_slug_is_a_noop(self, api_client, host):
        event = _make_event("Potluck", created_by=host)
        resp = _patch_slug(api_client, event, "potluck", host)
        assert resp.status_code == 200
        assert not EventSlugAlias.objects.exists()


@pytest.mark.django_db
class TestSlugValidation:
    @pytest.mark.parametrize(
        "slug",
        [
            "",
            "has spaces",
            "emoji-🌱",
            "-leading",
            "trailing-",
            "a/b",
            "762f5f57-6519-4a67-9b71-226df2e8d89c",
            "x" * 81,
        ],
    )
    def test_invalid_slug_rejected(self, api_client, host, slug):
        event = _make_event("Potluck", created_by=host)
        resp = _patch_slug(api_client, event, slug, host)
        assert resp.status_code == 422
        event.refresh_from_db()
        assert event.slug == "potluck"

    def test_taken_by_another_event(self, api_client, host):
        _make_event("Picnic")
        event = _make_event("Potluck", created_by=host)
        resp = _patch_slug(api_client, event, "picnic", host)
        assert resp.status_code == 409
        assert resp.json()["detail"][0]["code"] == "event.slug_taken"

    def test_taken_by_another_events_old_slug(self, api_client, host):
        other = _make_event("Picnic", created_by=host)
        _patch_slug(api_client, other, "big-picnic", host)
        event = _make_event("Potluck", created_by=host)
        resp = _patch_slug(api_client, event, "picnic", host)
        assert resp.status_code == 409

    @pytest.mark.parametrize("slug", ["add", "mine", "manage"])
    def test_reserved_route_slug_rejected(self, api_client, host, slug):
        event = _make_event("Potluck", created_by=host)
        resp = _patch_slug(api_client, event, slug, host)
        assert resp.status_code == 409


@pytest.mark.django_db
class TestOldSlugsKeepResolving:
    def test_old_slug_resolves_after_rename(self, api_client, host):
        event = _make_event("Potluck", created_by=host)
        _patch_slug(api_client, event, "summer-potluck", host)
        resp = api_client.get("/api/community/events/potluck/")
        assert resp.status_code == 200
        assert resp.json()["id"] == str(event.id)
        assert resp.json()["slug"] == "summer-potluck"

    def test_renaming_back_reclaims_old_slug(self, api_client, host):
        event = _make_event("Potluck", created_by=host)
        _patch_slug(api_client, event, "summer-potluck", host)
        resp = _patch_slug(api_client, event, "potluck", host)
        assert resp.status_code == 200
        assert list(EventSlugAlias.objects.values_list("slug", flat=True)) == ["summer-potluck"]
        assert Event.objects.get(event_lookup_q("potluck")).pk == event.pk
