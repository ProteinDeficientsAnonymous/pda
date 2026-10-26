from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone
from notifications.models import SseTicket


@pytest.mark.django_db
def test_purges_used_and_expired_sse_tickets(test_user):
    fresh = SseTicket.mint_for_user(test_user)
    used = SseTicket.mint_for_user(test_user)
    SseTicket.objects.filter(pk=used.pk).update(used=True)
    expired = SseTicket.mint_for_user(test_user)
    SseTicket.objects.filter(pk=expired.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
    out = StringIO()

    call_command("cleanup_notifications", stdout=out)

    assert list(SseTicket.objects.values_list("pk", flat=True)) == [fresh.pk]
    assert "Deleted 2 used or expired SSE tickets" in out.getvalue()
