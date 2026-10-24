from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone
from mcp_gateway.models import OAuthAuthRequest, OAuthClient, OAuthGrant

from tests._mcp_helpers import make_client, make_grant, make_request


def run() -> str:
    out = StringIO()
    call_command("prune_mcp_oauth", stdout=out)
    return out.getvalue()


def age_client(client: OAuthClient, days: int) -> None:
    OAuthClient.objects.filter(pk=client.pk).update(
        created_at=timezone.now() - timedelta(days=days)
    )


def expire_request(request: OAuthAuthRequest, ago: timedelta) -> None:
    OAuthAuthRequest.objects.filter(pk=request.pk).update(expires_at=timezone.now() - ago)


@pytest.mark.django_db
class TestPruneMcpOAuth:
    def test_deletes_auth_requests_expired_over_a_day_ago(self):
        client = make_client()
        stale = make_request(client)
        expire_request(stale, timedelta(days=2))
        just_expired = make_request(client)
        expire_request(just_expired, timedelta(minutes=5))
        pending = make_request(client)

        run()

        remaining = set(OAuthAuthRequest.objects.values_list("pk", flat=True))
        assert remaining == {just_expired.pk, pending.pk}

    def test_deletes_old_clients_that_never_got_a_grant(self):
        unused = make_client()
        age_client(unused, 8)
        fresh = make_client()

        run()

        assert not OAuthClient.objects.filter(pk=unused.pk).exists()
        assert OAuthClient.objects.filter(pk=fresh.pk).exists()

    def test_keeps_old_clients_with_a_grant_even_if_revoked(self, test_user):
        connected = make_client()
        make_grant(test_user, connected)
        revoked = make_client()
        OAuthGrant.objects.filter(pk=make_grant(test_user, revoked).pk).update(
            revoked_at=timezone.now()
        )
        for client in (connected, revoked):
            age_client(client, 30)

        run()

        assert OAuthClient.objects.filter(pk__in=[connected.pk, revoked.pk]).count() == 2

    def test_reports_what_it_deleted(self):
        expire_request(make_request(), timedelta(days=2))
        age_client(make_client(), 8)

        assert run().strip() == "Deleted 1 expired auth requests and 1 unused clients"
