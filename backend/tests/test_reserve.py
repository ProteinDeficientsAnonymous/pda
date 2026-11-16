from datetime import date
from decimal import Decimal

import pytest
from community.models import ReserveEntry, ReserveEntryKind


@pytest.mark.django_db
class TestGetReserve:
    def test_get_reserve_public_ordered_by_date(self, api_client):
        ReserveEntry.objects.create(
            label="spicy moon brunch",
            occurred_on=date(2026, 5, 9),
            collected=Decimal("1440.00"),
            paid_out=Decimal("1479.64"),
        )
        ReserveEntry.objects.create(
            label="donut walk",
            occurred_on=date(2026, 4, 25),
            collected=Decimal("350.00"),
            paid_out=Decimal("265.47"),
            facilitator_drinks=Decimal("10.50"),
        )

        response = api_client.get("/api/community/reserve/")

        assert response.status_code == 200
        body = response.json()
        assert [e["label"] for e in body["entries"]] == ["donut walk", "spicy moon brunch"]
        assert body["entries"][0]["left_over"] == "74.03"
        assert body["entries"][1]["left_over"] == "-39.64"
        assert body["updated_at"] is not None

    def test_get_reserve_empty(self, api_client):
        response = api_client.get("/api/community/reserve/")

        assert response.status_code == 200
        assert response.json() == {"entries": [], "updated_at": None}

    def test_get_reserve_groups_events_then_costs_then_donations(self, api_client):
        def make(label, kind, day):
            ReserveEntry.objects.create(label=label, kind=kind, occurred_on=date(2026, 5, day))

        make("donation", ReserveEntryKind.DONATION, 1)
        make("stickers", ReserveEntryKind.COST, 2)
        make("late walk", ReserveEntryKind.EVENT, 30)
        make("early walk", ReserveEntryKind.EVENT, 3)

        response = api_client.get("/api/community/reserve/")

        assert response.status_code == 200
        entries = response.json()["entries"]
        assert [e["label"] for e in entries] == ["early walk", "late walk", "stickers", "donation"]
        assert entries[-1]["kind"] == "donation"
