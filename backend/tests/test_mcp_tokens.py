import hashlib

import pytest
from mcp_gateway.models import OAuthClient, OAuthGrant
from mcp_gateway.tokens import hash_secret, new_secret


def test_hash_secret_is_stable_sha256():
    assert hash_secret("abc") == hashlib.sha256(b"abc").hexdigest()


def test_new_secret_is_unique_and_long():
    a, b = new_secret(), new_secret()
    assert a != b and len(a) >= 40


@pytest.mark.django_db
def test_grant_revoked_flag(test_user):
    client = OAuthClient.objects.create(client_id="c1", info={})
    grant = OAuthGrant.objects.create(user=test_user, client=client)
    assert grant.revoked_at is None
