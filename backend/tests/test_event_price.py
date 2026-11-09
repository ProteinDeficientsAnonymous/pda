import importlib
import json
from decimal import Decimal

import pytest
from community.events.price import parse_price, price_text
from community.models import Event
from community.validation import Code, ValidationException

from tests._time import future_iso

migration = importlib.import_module("community.migrations.0131_event_price_decimal")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, None),
        ("", None),
        ("   ", None),
        ("10", Decimal("10.00")),
        ("$10", Decimal("10.00")),
        (" $ 1,250.5 ", Decimal("1250.50")),
        (12.345, Decimal("12.35")),
    ],
)
def test_parse_price_accepts_amounts(raw, expected):
    assert parse_price(raw) == expected


@pytest.mark.parametrize("raw", ["free", "$10-20", "0", "-5", "NaN", "100000"])
def test_parse_price_rejects_non_amounts(raw):
    with pytest.raises(ValidationException) as exc:
        parse_price(raw)
    assert (exc.value.code, exc.value.field) == (Code.Event.PRICE_INVALID, "price")


@pytest.mark.parametrize(
    ("amount", "expected"),
    [(None, ""), (Decimal("10.00"), "10"), (Decimal("33.50"), "33.50"), ("15", "15")],
)
def test_price_text(amount, expected):
    assert price_text(amount) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("14", "14"),
        ("$21", "21"),
        ("33.50", "33.50"),
        ("$10 deposit", "10"),
        ("~$35 - ~$60 sliding scale + cookbook", "35"),
        ("", None),
        ("pwyc", None),
        ("$0", None),
    ],
)
def test_migration_keeps_the_first_amount(raw, expected):
    assert migration.numeric_text(raw) == expected


@pytest.mark.django_db
class TestEventPriceApi:
    def _create(self, api_client, auth_headers, price):
        return api_client.post(
            "/api/community/events/",
            data=json.dumps({"title": "Dinner", "start_datetime": future_iso(), "price": price}),
            content_type="application/json",
            **auth_headers,
        )

    def test_create_stores_a_decimal_and_returns_text(self, api_client, auth_headers):
        resp = self._create(api_client, auth_headers, "$12.50")
        assert resp.status_code == 201
        assert resp.json()["price"] == "12.50"
        assert Event.objects.get(pk=resp.json()["id"]).price == Decimal("12.50")

    def test_create_rejects_free_text(self, api_client, auth_headers):
        resp = self._create(api_client, auth_headers, "sliding scale")
        assert resp.status_code == 422
        assert [e["code"] for e in resp.json()["detail"]] == [Code.Event.PRICE_INVALID]

    def test_patch_blank_clears_the_price(self, api_client, auth_headers):
        event_id = self._create(api_client, auth_headers, "10").json()["id"]
        resp = api_client.patch(
            f"/api/community/events/{event_id}/",
            data=json.dumps({"price": ""}),
            content_type="application/json",
            **auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["price"] == ""
        assert Event.objects.get(pk=event_id).price is None
