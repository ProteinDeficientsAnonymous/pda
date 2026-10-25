import json

import pytest
from audit.models import AuditLogEntry
from community.models import EventRSVP
from django.core.cache import caches
from django.utils import timezone
from mcp_gateway.cashapp_review import csv_digest, review_cache_key
from users.permissions import PermissionKey

from tests._cashapp_helpers import csv_line
from tests._mcp_payments_helpers import (
    make_csv_text,
    make_draft,
    make_event,
    make_guests,
    make_importer,
    make_user,
    payment_date,
    review,
    verified_ids,
)
from tests.test_mcp_events_write import _error, _run
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


@pytest.fixture
def review_id(importer, event, guests, csv_text):
    return review(importer, event, csv_text)["review_id"]


def _verify(user, event, review_id, assignments, **extra) -> dict:
    arguments = {"event": str(event.pk), "review_id": review_id, "assignments": assignments}
    return _run(user, "verify_cashapp_payments", **arguments, **extra)


def _refused(user, event, review_id, assignments, **extra) -> str:
    arguments = {"event": str(event.pk), "review_id": review_id, "assignments": assignments}
    return _error(user, "verify_cashapp_payments", **arguments, **extra)


def _pay(payment_id, *users) -> dict:
    return {"payment_id": payment_id, "user_ids": [str(u.pk) for u in users]}


def _names(people) -> list[str]:
    return [p["name"] for p in people]


def test_verify_tool_needs_import_payments(test_user, importer, event, review_id, guests):
    assert "verify_cashapp_payments" not in _tool_names(test_user)
    assert "verify_cashapp_payments" in _tool_names(importer)
    assert "permission" in _refused(test_user, event, review_id, [_pay("tx1", guests["alex"])])


def test_import_permission_alone_cannot_verify(event, review_id, guests):
    import_only = make_user("+12025557201", PermissionKey.IMPORT_PAYMENTS)
    key = review_cache_key(import_only.pk, str(event.pk), review_id)
    caches["ratelimit"].set(key, make_csv_text(), 60)
    error = json.loads(_refused(import_only, event, review_id, [_pay("tx1", guests["alex"])]))
    assert error["status"] == 403
    assert not verified_ids(event)


def test_another_members_draft_is_refused(importer, review_id, guests):
    draft = make_draft(make_user("+12025557203", first="Other", last="Host"))
    error = _refused(importer, draft, review_id, [_pay("tx1", guests["alex"])])
    assert json.loads(error)["status"] == 403


def test_missing_or_expired_review_is_refused(importer, event, guests, review_id):
    alex = [_pay("tx1", guests["alex"])]
    assert "review expired" in _refused(importer, event, "0" * 64, alex)
    caches["ratelimit"].delete(review_cache_key(importer.pk, str(event.pk), review_id))
    assert "review expired" in _refused(importer, event, review_id, alex)


def test_another_users_review_id_is_refused(event, guests, review_id):
    co_host = make_user("+12025557204", PermissionKey.IMPORT_PAYMENTS, first="Co", last="Host")
    event.co_hosts.add(co_host)
    assert "review expired" in _refused(co_host, event, review_id, [_pay("tx1", guests["alex"])])


def test_preview_has_no_side_effects(importer, event, guests, review_id):
    preview = _verify(importer, event, review_id, [_pay("tx2", guests["sam"], guests["jo"])])

    assert _names(preview["to_verify"]) == ["Jo Park", "Sam Lee"]
    payment = preview["to_verify"][0]["payments"][0]
    assert (payment["payment_id"], payment["confidence"], payment["covers_people"]) == (
        "tx2",
        "confident",
        "2",
    )
    assert payment["reason"]
    assert preview["to_verify"][0]["said_paid"] is False
    assert preview["confirm_token"]
    assert not verified_ids(event)
    assert not AuditLogEntry.objects.filter(action="guest_payment_changed").exists()


def test_confirm_verifies_via_mcp_and_recomputes_the_gap_list(importer, event, guests, review_id):
    assignments = [_pay("tx1", guests["alex"]), _pay("tx4", guests["riley"])]
    token = _verify(importer, event, review_id, assignments)["confirm_token"]

    result = _verify(importer, event, review_id, assignments, confirm_token=token)

    assert set(_names(result["verified"])) == {"Alex Kim", "Riley Chen"}
    assert result["event_verified_total"] == 2
    assert _names(result["gap_list"]) == ["Casey Wu"]
    assert verified_ids(event) == {str(guests["alex"].pk), str(guests["riley"].pk)}
    entries = AuditLogEntry.objects.filter(action="guest_payment_changed")
    assert entries.count() == 2
    for entry in entries:
        assert (entry.actor, entry.details["via"]) == (importer, "mcp")
        assert entry.details["source"] == "cashapp_import"


def test_token_is_bound_to_the_exact_selection(importer, event, guests, csv_text, review_id):
    alex = [_pay("tx1", guests["alex"])]
    token = _verify(importer, event, review_id, alex)["confirm_token"]

    pair = [_pay("tx2", guests["sam"], guests["jo"])]
    assert "fresh preview" in _refused(importer, event, review_id, pair, confirm_token=token)
    other_csv = make_csv_text(csv_line(tx="tx9", date=payment_date(), name="Someone Else"))
    other_id = review(importer, event, other_csv)["review_id"]
    assert "fresh preview" in _refused(importer, event, other_id, alex, confirm_token=token)
    co_host = make_user("+12025557204", PermissionKey.IMPORT_PAYMENTS, first="Co", last="Host")
    event.co_hosts.add(co_host)
    assert review(co_host, event, csv_text)["review_id"] == review_id
    assert "fresh preview" in _refused(co_host, event, review_id, alex, confirm_token=token)
    assert not verified_ids(event)


def test_token_goes_stale_when_a_selected_guest_is_verified_first(
    importer, event, guests, review_id
):
    assignments = [_pay("tx1", guests["alex"]), _pay("tx4", guests["riley"])]
    token = _verify(importer, event, review_id, assignments)["confirm_token"]
    EventRSVP.objects.filter(user=guests["alex"]).update(payment_verified_at=timezone.now())
    assert "fresh preview" in _refused(importer, event, review_id, assignments, confirm_token=token)


def test_unrelated_verification_keeps_the_token_valid(importer, event, guests, review_id):
    alex = [_pay("tx1", guests["alex"])]
    token = _verify(importer, event, review_id, alex)["confirm_token"]
    EventRSVP.objects.filter(user=guests["casey"]).update(payment_verified_at=timezone.now())
    assert _names(_verify(importer, event, review_id, alex, confirm_token=token)["verified"]) == [
        "Alex Kim"
    ]


def test_token_is_single_use(importer, event, guests, review_id):
    alex = [_pay("tx1", guests["alex"])]
    token = _verify(importer, event, review_id, alex)["confirm_token"]
    limit_key = f"rl:verify_guest_payments:{importer.pk}"
    caches["ratelimit"].set(limit_key, 10, 60)
    assert (
        json.loads(_refused(importer, event, review_id, alex, confirm_token=token))["status"] == 429
    )
    caches["ratelimit"].delete(limit_key)
    assert "already used" in _refused(importer, event, review_id, alex, confirm_token=token)
    assert not verified_ids(event)


def test_a_payment_cant_cover_more_people_than_its_amount(importer, event, guests, csv_text):
    EventRSVP.objects.filter(user=guests["alex"]).update(has_plus_one=True)
    review_id = review(importer, event, csv_text)["review_id"]
    error = _refused(importer, event, review_id, [_pay("tx1", guests["alex"])])
    assert "covers at most 1 people, but these guests are 2 with plus-ones" in error


def test_one_guest_covered_by_two_payments(importer, event, guests):
    second = csv_line(tx="tx5", date=payment_date(), name="Alex Kim")
    review_id = review(importer, event, make_csv_text(second))["review_id"]
    assignments = [_pay("tx1", guests["alex"]), _pay("tx5", guests["alex"])]

    preview = _verify(importer, event, review_id, assignments)
    assert [p["payment_id"] for p in preview["to_verify"][0]["payments"]] == ["tx1", "tx5"]
    result = _verify(
        importer, event, review_id, assignments, confirm_token=preview["confirm_token"]
    )
    assert _names(result["verified"]) == ["Alex Kim"]


@pytest.mark.parametrize(
    "case",
    [
        ("tx1", "sam", "can only verify its matched guests or candidates"),
        ("tx3", "alex", "didn't match any guest"),
        ("tx6", "sam", "is an amount mismatch lead"),
        ("tx7", "alex", "couldn't be read"),
        ("nope", "alex", "isn't in this review"),
    ],
)
def test_assignment_outside_the_review_is_refused(importer, event, guests, case):
    date = payment_date()
    csv_text = make_csv_text(
        csv_line(tx="tx6", date=date, name="Sam Lee", amount="$7"),
        csv_line(tx="tx7", date=date, name="Alex Kim", amount="lots"),
    )
    review_id = review(importer, event, csv_text)["review_id"]
    payment_id, user, message = case
    assert message in _refused(importer, event, review_id, [_pay(payment_id, guests[user])])
    assert not verified_ids(event)


def test_each_payment_listed_once(importer, event, guests, review_id):
    assignments = [_pay("tx2", guests["sam"]), _pay("tx2", guests["jo"])]
    assert "each payment_id once" in _refused(importer, event, review_id, assignments)


def test_already_verified_guests_are_dropped(importer, event, guests, review_id):
    EventRSVP.objects.filter(user=guests["alex"]).update(payment_verified_at=timezone.now())
    alex = [_pay("tx1", guests["alex"])]
    assert "already verified" in _refused(importer, event, review_id, alex)

    preview = _verify(importer, event, review_id, [*alex, _pay("tx2", guests["sam"], guests["jo"])])
    assert _names(preview["to_verify"]) == ["Jo Park", "Sam Lee"]
    assert _names(preview["already_verified"]) == ["Alex Kim"]


def test_review_id_is_the_csv_digest(review_id, csv_text):
    assert review_id == csv_digest(csv_text)
