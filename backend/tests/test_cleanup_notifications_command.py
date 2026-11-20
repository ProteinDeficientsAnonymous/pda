from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from notifications.models import Notification, SseTicket


def _notification(user, *, is_read: bool, age_days: int) -> Notification:
    notification = Notification.objects.create(recipient=user, message="hi", is_read=is_read)
    created_at = timezone.now() - timedelta(days=age_days)
    Notification.objects.filter(pk=notification.pk).update(created_at=created_at)
    return notification


def _ticket(user, *, used: bool, expired: bool) -> SseTicket:
    ticket = SseTicket.mint_for_user(user)
    expires_at = timezone.now() - timedelta(seconds=1) if expired else ticket.expires_at
    SseTicket.objects.filter(pk=ticket.pk).update(used=used, expires_at=expires_at)
    return ticket


@pytest.mark.django_db
def test_purges_expired_sse_tickets_only(test_user):
    fresh = _ticket(test_user, used=False, expired=False)
    # Used tickets expire within the 60s TTL, so expiry alone catches them on a later run.
    used_unexpired = _ticket(test_user, used=True, expired=False)
    _ticket(test_user, used=True, expired=True)
    _ticket(test_user, used=False, expired=True)
    out = StringIO()

    call_command("cleanup_notifications", stdout=out)

    assert set(SseTicket.objects.values_list("pk", flat=True)) == {fresh.pk, used_unexpired.pk}
    assert "Deleted 2 expired SSE tickets" in out.getvalue()


@pytest.mark.django_db
def test_purges_only_old_read_notifications(test_user):
    recent_read = _notification(test_user, is_read=True, age_days=89)
    old_unread = _notification(test_user, is_read=False, age_days=91)
    _notification(test_user, is_read=True, age_days=91)
    out = StringIO()

    call_command("cleanup_notifications", stdout=out)

    assert set(Notification.objects.values_list("pk", flat=True)) == {recent_read.pk, old_unread.pk}
    assert "Deleted 1 old read notifications" in out.getvalue()


@pytest.mark.django_db
def test_deletes_backlog_across_multiple_batches(test_user, monkeypatch):
    monkeypatch.setattr("notifications.management.commands.cleanup_notifications._BATCH_SIZE", 2)
    fresh = _ticket(test_user, used=False, expired=False)
    for _ in range(5):
        _ticket(test_user, used=True, expired=True)
        _notification(test_user, is_read=True, age_days=91)
    out = StringIO()

    with CaptureQueriesContext(connection) as ctx:
        call_command("cleanup_notifications", stdout=out)

    assert set(SseTicket.objects.values_list("pk", flat=True)) == {fresh.pk}
    assert not Notification.objects.exists()
    assert "Deleted 5 expired SSE tickets" in out.getvalue()
    assert "Deleted 5 old read notifications" in out.getvalue()
    deletes = [q["sql"] for q in ctx.captured_queries if q["sql"].startswith("DELETE")]
    assert len(deletes) == 6
