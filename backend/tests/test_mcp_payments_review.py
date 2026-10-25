import json
import uuid

import pytest
from django.core.cache import caches
from mcp_gateway.cashapp_review import csv_digest, review_cache_key
from mcp_gateway.tools.payments_review import MAX_CSV_CHARS
from users.permissions import PermissionKey

from tests._mcp_payments_helpers import (
    make_csv_text,
    make_draft,
    make_event,
    make_guests,
    make_importer,
    make_user,
    review,
    review_refused,
    verified_ids,
)
from tests.test_mcp_surveys_read import _tool_names

pytestmark = pytest.mark.django_db(transaction=True, serialized_rollback=True)


@pytest.fixture
def importer(db):
    return make_importer()


@pytest.fixture
def event(test_user, importer):
    return make_event(test_user, co_host=importer)


@pytest.fixture
def guests(event):
    return make_guests(event)


@pytest.fixture
def csv_text():
    return make_csv_text()


def test_review_tool_needs_import_payments(test_user, importer, event, csv_text):
    assert "review_cashapp_payments" not in _tool_names(test_user)
    assert "review_cashapp_payments" in _tool_names(importer)
    assert "permission" in review_refused(test_user, str(event.pk), csv_text)


def test_import_permission_alone_cannot_see_payments(test_user, csv_text):
    import_only = make_user("+12025557201", PermissionKey.IMPORT_PAYMENTS)
    event = make_event(test_user)
    error = json.loads(review_refused(import_only, str(event.pk), csv_text))
    assert (error["status"], error["detail"][0]["code"]) == (403, "perm.denied")


def test_manage_events_holder_can_review(test_user, event, guests, csv_text):
    manager = make_user("+12025557202", PermissionKey.IMPORT_PAYMENTS, PermissionKey.MANAGE_EVENTS)
    assert review(manager, event, csv_text)["counts"]["confident"] == 2


def test_another_members_draft_is_refused(importer, csv_text):
    other = make_user("+12025557203", first="Other", last="Host")
    error = json.loads(review_refused(importer, str(make_draft(other).pk), csv_text))
    assert error["status"] == 403


def test_review_groups_matches_and_leads_with_the_gap_list(importer, event, guests, csv_text):
    result = review(importer, event, csv_text)

    assert list(result)[:3] == ["event", "review_id", "gap_list"]
    gap = {g["name"]: g["reason"] for g in result["gap_list"]}
    assert gap == {"Riley Chen": "unsure_match_pending", "Casey Wu": "attending_paid_event"}
    assert [p["payment_id"] for p in result["confident"]] == ["tx1", "tx2"]
    assert {g["name"] for g in result["confident"][1]["guests"]} == {"Sam Lee", "Jo Park"}
    unsure = result["unsure"][0]
    assert (unsure["payment_id"], unsure["candidates"][0]["name"]) == ("tx4", "Riley Chen")
    assert [p["payment_id"] for p in result["unplaced_payments"]] == ["tx3"]
    assert result["counts"] == {
        "csv_rows": 4,
        "confident": 2,
        "unsure": 1,
        "unplaced": 1,
        "gap": 2,
        "already_verified": 0,
    }
    assert result["price"] == {"text": "$15", "read_as": "exact", "low": "15", "high": "15"}
    assert result["confident"][0]["amount"] == "15"
    assert not verified_ids(event)


def test_review_caches_the_csv_for_an_hour_under_user_event_and_digest(
    importer, event, guests, csv_text
):
    review_id = review(importer, event, csv_text)["review_id"]
    assert review_id == csv_digest(csv_text)
    key = review_cache_key(importer.pk, str(event.pk), review_id)
    assert caches["ratelimit"].get(key) == csv_text


def test_review_reports_unreadable_csv_like_the_website(importer, event):
    error = json.loads(review_refused(importer, str(event.pk), "a,b\n1,2\n"))
    assert (error["status"], error["detail"][0]["code"]) == (
        400,
        "cashapp_import.csv_missing_columns",
    )


def test_review_unknown_event_is_404(importer, csv_text):
    assert json.loads(review_refused(importer, str(uuid.uuid4()), csv_text))["status"] == 404


def test_csv_text_is_bounded(importer, event):
    assert "csv_text" in review_refused(importer, str(event.pk), "x" * (MAX_CSV_CHARS + 1))
