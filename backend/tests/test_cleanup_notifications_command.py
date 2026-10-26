from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone
from notifications.models import SseTicket


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
