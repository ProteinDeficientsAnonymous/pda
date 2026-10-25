from datetime import datetime, timedelta
from urllib.parse import urlencode

import pytest
from community.models import Event
from django.utils import timezone
from users.models import User

WINDOW_START = timezone.now().replace(microsecond=0) + timedelta(days=40)
WINDOW_END = WINDOW_START + timedelta(days=30)


def _event(title: str, start: datetime | None, end: datetime | None = None, **extra) -> Event:
    return Event.objects.create(title=title, start_datetime=start, end_datetime=end, **extra)


def _titles(api_client, **params) -> set[str]:
    query = f"?{urlencode(params)}" if params else ""
    response = api_client.get(f"/api/community/events/{query}")
    assert response.status_code == 200
    return {e["title"] for e in response.json()}


@pytest.fixture
def events(db):
    day = timedelta(days=1)
    _event("before", WINDOW_START - 3 * day, WINDOW_START - 2 * day)
    _event("spans start", WINDOW_START - day, WINDOW_START + day)
    _event("inside", WINDOW_START + 5 * day, WINDOW_START + 5 * day + timedelta(hours=2))
    _event("inside no end", WINDOW_START + 6 * day)
    _event("no end, running at start", WINDOW_START - timedelta(hours=1))
    _event("after", WINDOW_END + day)
    _event("tbd", None, datetime_tbd=True)
    _event("partiful", WINDOW_START + 2 * day, is_partiful_import=True)
    _event("legacy", WINDOW_START + 3 * day, is_legacy=True)


@pytest.mark.django_db
class TestListEventsWindow:
    def test_no_params_keeps_every_event(self, api_client, events):
        assert _titles(api_client) == {
            "before",
            "spans start",
            "inside",
            "inside no end",
            "no end, running at start",
            "after",
            "tbd",
            "partiful",
            "legacy",
        }

    def test_window_keeps_overlapping_dated_events(self, api_client, events):
        titles = _titles(api_client, start=WINDOW_START.isoformat(), end=WINDOW_END.isoformat())
        assert titles == {
            "spans start",
            "inside",
            "inside no end",
            "no end, running at start",
            "partiful",
            "legacy",
        }

    def test_start_only_keeps_everything_from_then_on(self, api_client, events):
        titles = _titles(api_client, start=WINDOW_START.isoformat(), include_imported="false")
        assert titles == {
            "spans start",
            "inside",
            "inside no end",
            "no end, running at start",
            "after",
        }

    def test_include_imported_false_drops_partiful_and_legacy(self, api_client, events):
        titles = _titles(api_client, include_imported="false")
        assert "partiful" not in titles
        assert "legacy" not in titles
        assert {"before", "tbd"} <= titles

    def test_naive_datetimes_are_read_as_utc(self, api_client, events):
        naive = WINDOW_START.astimezone(timezone.UTC).replace(tzinfo=None)
        titles = _titles(api_client, start=naive.isoformat(), end=WINDOW_END.isoformat())
        assert "inside" in titles
        assert "before" not in titles


@pytest.fixture
def hosted_events(test_user):
    now = timezone.now()
    other = User.objects.create_user(phone_number="+12025550188", password="Testpass123!")
    _event("mine", now + timedelta(days=2), created_by=test_user)
    _event("cohosted", now + timedelta(days=3), created_by=other).co_hosts.add(test_user)
    _event("theirs", now + timedelta(days=1), created_by=other)
    _event("mine past", now - timedelta(days=2), created_by=test_user)
    _event("mine ended", now - timedelta(hours=3), now - timedelta(minutes=1), created_by=test_user)
    _event("mine ongoing", now - timedelta(hours=1), created_by=test_user)
    _event("mine tbd", None, datetime_tbd=True, created_by=test_user)
    _event("mine tbd old date", now - timedelta(days=9), datetime_tbd=True, created_by=test_user)


@pytest.mark.django_db
class TestListEventsScope:
    def _titles(self, api_client, auth_headers, **params) -> set[str]:
        response = api_client.get(f"/api/community/events/?{urlencode(params)}", **auth_headers)
        assert response.status_code == 200
        return {e["title"] for e in response.json()}

    def test_defaults_unchanged(self, api_client, auth_headers, hosted_events):
        assert len(self._titles(api_client, auth_headers)) == 8

    def test_hosted_keeps_created_and_cohosted(self, api_client, auth_headers, hosted_events):
        titles = self._titles(api_client, auth_headers, hosted="true")
        assert "theirs" not in titles and {"mine", "cohosted", "mine past"} <= titles

    def test_upcoming_matches_is_past(self, api_client, auth_headers, hosted_events):
        titles = self._titles(api_client, auth_headers, upcoming="true")
        expected = {e.title for e in Event.objects.all() if not e.is_past}
        assert titles == expected
        assert {"mine ongoing", "mine tbd", "mine tbd old date"} <= titles
        assert not {"mine past", "mine ended"} & titles

    def test_hosted_requires_auth(self, api_client, hosted_events):
        response = api_client.get("/api/community/events/?hosted=true")
        assert response.status_code == 403
