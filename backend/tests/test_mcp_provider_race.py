import asyncio
import threading
import time
from collections.abc import Awaitable, Callable

import pytest
from asgiref.sync import ThreadSensitiveContext, sync_to_async
from django import db
from django.db import transaction
from django.utils import timezone
from mcp.server.auth.provider import TokenError
from mcp.shared.auth import OAuthToken as TokenResponse
from mcp_gateway.models import OAuthAuthCode, OAuthToken
from mcp_gateway.provider import PdaOAuthProvider, issue_auth_code
from mcp_gateway.tokens import hash_secret

from tests.test_mcp_provider import _client_info, _connect, _pending_request

if db.connection.vendor != "postgresql":
    pytest.skip("needs concurrent postgres writers", allow_module_level=True)

pytestmark = pytest.mark.django_db(transaction=True, serialized_rollback=True)

RACERS = 8


def _attempt(exchange: Callable[[], Awaitable[TokenResponse]]) -> object:
    async def run() -> object:
        # Each context gets its own ORM thread, so each attempt has its own DB connection.
        async with ThreadSensitiveContext():
            try:
                return await exchange()
            except TokenError as e:
                return e
            finally:
                await sync_to_async(db.connections.close_all)()

    return asyncio.run(run())


def _race(exchange: Callable[[], Awaitable[TokenResponse]]) -> list[object]:
    barrier = threading.Barrier(RACERS)
    results: list[object] = [None] * RACERS

    def run(i: int) -> None:
        barrier.wait()
        results[i] = _attempt(exchange)

    threads = [threading.Thread(target=run, args=(i,)) for i in range(RACERS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results


def _attempt_while_claimed(
    claim: Callable[[], object], exchange: Callable[[], Awaitable[TokenResponse]]
) -> object:
    claimed = threading.Event()

    def hold_claim_uncommitted() -> None:
        try:
            with transaction.atomic():
                claim()
                claimed.set()
                time.sleep(0.5)
        finally:
            db.connections.close_all()

    holder = threading.Thread(target=hold_claim_uncommitted)
    holder.start()
    claimed.wait()
    result = _attempt(exchange)
    holder.join()
    return result


def _winners(results: list[object]) -> int:
    assert all(isinstance(r, TokenResponse | TokenError) for r in results), results
    return sum(isinstance(r, TokenResponse) for r in results)


def test_concurrent_code_exchange_only_one_succeeds(test_user):
    provider = PdaOAuthProvider()
    code = issue_auth_code(_pending_request(provider), test_user)
    loaded = asyncio.run(provider.load_authorization_code(_client_info(), code))
    assert loaded is not None
    results = _race(lambda: provider.exchange_authorization_code(_client_info(), loaded))
    assert _winners(results) == 1
    assert OAuthToken.objects.filter(kind=OAuthToken.Kind.REFRESH).count() == 1


def test_concurrent_refresh_exchange_only_one_succeeds(test_user):
    provider = PdaOAuthProvider()
    tokens = _connect(provider, test_user)
    assert tokens.refresh_token is not None
    old = asyncio.run(provider.load_refresh_token(_client_info(), tokens.refresh_token))
    assert old is not None
    results = _race(lambda: provider.exchange_refresh_token(_client_info(), old, ["pda"]))
    assert _winners(results) == 1
    assert OAuthToken.objects.filter(kind=OAuthToken.Kind.REFRESH).count() == 2


def test_code_exchange_loses_to_in_flight_claim(test_user):
    provider = PdaOAuthProvider()
    code = issue_auth_code(_pending_request(provider), test_user)
    loaded = asyncio.run(provider.load_authorization_code(_client_info(), code))
    assert loaded is not None
    result = _attempt_while_claimed(
        lambda: OAuthAuthCode.objects.update(used_at=timezone.now()),
        lambda: provider.exchange_authorization_code(_client_info(), loaded),
    )
    assert isinstance(result, TokenError)
    assert not OAuthToken.objects.exists()


def test_refresh_exchange_loses_to_in_flight_claim(test_user):
    provider = PdaOAuthProvider()
    tokens = _connect(provider, test_user)
    assert tokens.refresh_token is not None
    old = asyncio.run(provider.load_refresh_token(_client_info(), tokens.refresh_token))
    assert old is not None
    result = _attempt_while_claimed(
        lambda: OAuthToken.objects.filter(token_hash=hash_secret(old.token)).update(
            revoked_at=timezone.now()
        ),
        lambda: provider.exchange_refresh_token(_client_info(), old, ["pda"]),
    )
    assert isinstance(result, TokenError)
    assert OAuthToken.objects.count() == 2
