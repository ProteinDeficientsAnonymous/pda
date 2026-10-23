import hashlib

from mcp_gateway.tokens import hash_secret, new_secret


def test_hash_secret_is_stable_sha256():
    assert hash_secret("abc") == hashlib.sha256(b"abc").hexdigest()


def test_new_secret_is_unique_and_long():
    a, b = new_secret(), new_secret()
    assert a != b and len(a) >= 40
