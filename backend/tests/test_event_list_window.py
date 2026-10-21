from datetime import datetime, timedelta
from urllib.parse import urlencode

import pytest
from community.models import Event
from django.utils import timezone

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
