import uuid
from datetime import timedelta

import pytest
from audit.models import AuditLogEntry
from community._event_schemas import MAX_BULK_PAYMENT_VERIFY
from community._validation import Code
from community.models import EventRSVP, EventStatus, RSVPStatus
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from users.permissions import PermissionKey
from users.roles import Role

from tests._payment_helpers import create_paid_event

pytestmark = pytest.mark.django_db

URL = "/api/community/events/{event_id}/rsvps/payments/verify/"


def _headers(user):
    return {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(user).access_token}"}


def _user_with(django_user_model, phone: str, *permissions: str):
    user = django_user_model.objects.create_user(phone_number=phone, first_name="Imp")
    user.roles.add(Role.objects.create(name=f"role-{phone}", permissions=list(permissions)))
    return user


@pytest.fixture
def importer(django_user_model):
    return _user_with(
        django_user_model,
        "+14155550601",
        PermissionKey.IMPORT_PAYMENTS,
        PermissionKey.MANAGE_EVENTS,
    )


@pytest.fixture
def event(test_user):
    return create_paid_event(created_by=test_user)


def _guest(django_user_model, n: int, event, **rsvp_fields):
    user = django_user_model.objects.create_user(
        phone_number=f"+1415555070{n}", first_name=f"Guest{n}"
    )
    EventRSVP.objects.create(event=event, user=user, status=RSVPStatus.ATTENDING, **rsvp_fields)
    return user


def _verify(api_client, user, event_id, user_ids):
    return api_client.post(
        URL.format(event_id=event_id),
        {"user_ids": [str(uid) for uid in user_ids]},
        content_type="application/json",
        **_headers(user),
    )


def test_verifies_guests_and_skips_already_verified(api_client, importer, event, django_user_model):
    fresh = _guest(django_user_model, 1, event)
    done = _guest(
        django_user_model,
        2,
        event,
        paid_confirmed_at=timezone.now(),
        payment_verified_at=timezone.now(),
    )

    response = _verify(api_client, importer, event.id, [fresh.id, done.id, fresh.id])

    assert response.status_code == 200
    assert response.json() == {
        "verified_user_ids": [str(fresh.id)],
        "already_verified_user_ids": [str(done.id)],
        "event_verified_total": 2,
    }
    rsvp = EventRSVP.objects.get(event=event, user=fresh)
    assert rsvp.payment_verified_by == importer
    assert rsvp.paid_confirmed_at == rsvp.payment_verified_at


def test_audits_each_verification_as_a_cashapp_import(
    api_client, importer, event, django_user_model, django_capture_on_commit_callbacks
):
    guests = [_guest(django_user_model, n, event) for n in (1, 2)]

    with django_capture_on_commit_callbacks(execute=True):
        _verify(api_client, importer, event.id, [g.id for g in guests])

    entries = AuditLogEntry.objects.filter(action="guest_payment_changed", target_id=str(event.id))
    assert sorted(e.details["user_id"] for e in entries) == sorted(str(g.id) for g in guests)
    rows = {str(r.user_id): r for r in EventRSVP.objects.filter(event=event)}
    for entry in entries:
        row = rows[entry.details["user_id"]]
        assert entry.actor == importer
        assert entry.details["source"] == "cashapp_import"
        assert entry.details["host_stamped"] is False
        assert entry.details["payment_verified"] is True
        assert entry.details["payment_verified_by"] == str(importer.id)
        assert entry.details["paid_confirmed_at"] == row.paid_confirmed_at.isoformat()
        assert entry.details["payment_verified_at"] == row.payment_verified_at.isoformat()


def test_skipped_guests_get_no_audit_row(
    api_client, importer, event, django_user_model, django_capture_on_commit_callbacks
):
    done = _guest(django_user_model, 1, event, payment_verified_at=timezone.now())
    with django_capture_on_commit_callbacks(execute=True):
        _verify(api_client, importer, event.id, [done.id])
    assert not AuditLogEntry.objects.filter(action="guest_payment_changed").exists()


def test_unknown_or_non_guest_rejects_the_whole_batch(
    api_client, importer, event, django_user_model, django_capture_on_commit_callbacks
):
    guest = _guest(django_user_model, 1, event)
    other_event = create_paid_event(title="Other")
    elsewhere = _guest(django_user_model, 2, other_event)
    stranger = uuid.uuid4()

    with django_capture_on_commit_callbacks(execute=True):
        response = _verify(api_client, importer, event.id, [guest.id, elsewhere.id, stranger])

    assert response.status_code == 400
    detail = response.json()["detail"][0]
    assert detail["code"] == Code.Event.PAYMENT_VERIFY_NOT_GUESTS
    assert detail["params"]["user_ids"] == f"{elsewhere.id}, {stranger}"
    assert not EventRSVP.objects.filter(payment_verified_at__isnull=False).exists()
    assert not AuditLogEntry.objects.filter(action="guest_payment_changed").exists()


def test_event_host_without_import_permission_is_denied(
    api_client, test_user, event, django_user_model
):
    guest = _guest(django_user_model, 1, event)
    response = _verify(api_client, test_user, event.id, [guest.id])
    assert response.status_code == 403
    assert response.json()["detail"][0]["code"] == Code.Perm.DENIED
    assert EventRSVP.objects.get(user=guest).payment_verified_at is None


def test_missing_event_is_404(api_client, importer):
    response = _verify(api_client, importer, uuid.uuid4(), [uuid.uuid4()])
    assert response.status_code == 404


def test_requires_auth(api_client, event):
    response = api_client.post(
        URL.format(event_id=event.id),
        {"user_ids": [str(uuid.uuid4())]},
        content_type="application/json",
    )
    assert response.status_code == 401


@pytest.mark.parametrize("count", [0, MAX_BULK_PAYMENT_VERIFY + 1])
def test_batch_size_is_bounded(api_client, importer, event, count):
    response = _verify(api_client, importer, event.id, [uuid.uuid4() for _ in range(count)])
    assert response.status_code == 422


def test_is_rate_limited(api_client, importer, event, django_user_model):
    done = _guest(django_user_model, 1, event, payment_verified_at=timezone.now())
    codes = [_verify(api_client, importer, event.id, [done.id]).status_code for _ in range(11)]
    assert codes[:10] == [200] * 10
    assert codes[10] == 429


def test_import_permission_alone_cannot_see_payments(api_client, event, django_user_model):
    guest = _guest(django_user_model, 1, event)
    import_only = _user_with(django_user_model, "+14155550602", PermissionKey.IMPORT_PAYMENTS)
    response = _verify(api_client, import_only, event.id, [guest.id])
    assert response.status_code == 403
    assert EventRSVP.objects.get(user=guest).payment_verified_at is None


def test_co_host_with_import_permission_can_verify(api_client, event, django_user_model):
    guest = _guest(django_user_model, 1, event)
    co_host = _user_with(django_user_model, "+14155550603", PermissionKey.IMPORT_PAYMENTS)
    event.co_hosts.add(co_host)
    response = _verify(api_client, co_host, event.id, [guest.id])
    assert response.status_code == 200
    assert response.json()["verified_user_ids"] == [str(guest.id)]


def test_deleted_event_is_404(api_client, importer, event, django_user_model):
    guest = _guest(django_user_model, 1, event)
    event.status = EventStatus.DELETED
    event.save(update_fields=["status"])
    assert _verify(api_client, importer, event.id, [guest.id]).status_code == 404


@pytest.mark.parametrize("status", [RSVPStatus.MAYBE, RSVPStatus.CANT_GO])
def test_guests_outside_matchable_statuses_count_as_not_guests(
    api_client, importer, event, django_user_model, status
):
    guest = _guest(django_user_model, 1, event)
    EventRSVP.objects.filter(user=guest).update(status=status)
    response = _verify(api_client, importer, event.id, [guest.id])
    assert response.status_code == 400
    assert response.json()["detail"][0]["code"] == Code.Event.PAYMENT_VERIFY_NOT_GUESTS


def test_verifying_keeps_a_self_attested_paid_time(api_client, importer, event, django_user_model):
    attested_at = timezone.now() - timedelta(days=1)
    guest = _guest(django_user_model, 1, event, paid_confirmed_at=attested_at)
    _verify(api_client, importer, event.id, [guest.id])
    rsvp = EventRSVP.objects.get(user=guest)
    assert rsvp.paid_confirmed_at == attested_at
    assert rsvp.payment_verified_at is not None


def test_verifies_every_guest_in_one_update(api_client, importer, event, django_user_model):
    guests = [_guest(django_user_model, n, event) for n in range(1, 7)]
    table = EventRSVP._meta.db_table

    with CaptureQueriesContext(connection) as ctx:
        response = _verify(api_client, importer, event.id, [g.id for g in guests])

    assert response.status_code == 200
    updates = [q for q in ctx.captured_queries if q["sql"].startswith(f'UPDATE "{table}"')]
    assert len(updates) == 1
    rsvps = EventRSVP.objects.filter(event=event)
    assert all(r.payment_verified_by_id == importer.id for r in rsvps)
    assert all(r.paid_confirmed_at == r.payment_verified_at == r.updated_at for r in rsvps)
