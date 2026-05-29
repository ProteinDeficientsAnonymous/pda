"""Unit tests for config.ratelimit.client_ip XFF-spoofing resistance.

The login/magic-login rate limit keys on client_ip. A naive
``XFF.split(",")[0]`` trusts the attacker-controlled leftmost value, letting a
brute-forcer rotate spoofed headers into unlimited rate-limit buckets. These
tests pin the rightmost-untrusted-hop behaviour that defends against that.
"""

from config.ratelimit import client_ip
from django.test import RequestFactory


def _request(*, xff=None, remote_addr="10.0.0.1"):
    factory = RequestFactory()
    request = factory.get("/api/auth/login/")
    request.META["REMOTE_ADDR"] = remote_addr
    if xff is not None:
        request.META["HTTP_X_FORWARDED_FOR"] = xff
    else:
        request.META.pop("HTTP_X_FORWARDED_FOR", None)
    return request


class TestClientIp:
    def test_no_xff_falls_back_to_remote_addr(self):
        assert client_ip(_request(remote_addr="203.0.113.9")) == "203.0.113.9"

    def test_returns_anon_when_no_xff_and_no_remote_addr(self):
        request = _request()
        request.META.pop("REMOTE_ADDR", None)
        assert client_ip(request) == "anon"

    def test_single_trusted_proxy_returns_real_client(self, settings):
        # Railway: one proxy appends the IP it saw (the real client) to XFF.
        settings.TRUSTED_PROXY_COUNT = 1
        request = _request(xff="198.51.100.7")
        assert client_ip(request) == "198.51.100.7"

    def test_spoofed_leftmost_xff_is_ignored(self, settings):
        # Attacker prepends a forged value; the proxy appends the real client.
        # Rightmost-untrusted-hop logic must return the real client, not the spoof.
        settings.TRUSTED_PROXY_COUNT = 1
        request = _request(xff="1.2.3.4, 198.51.100.7")
        assert client_ip(request) == "198.51.100.7"

    def test_rotating_spoofed_xff_lands_in_same_bucket(self, settings):
        # The core of the brute-force defense: the attacker varies the spoofed
        # prefix on every request but always reaches us through one real proxy.
        # All variants must resolve to the SAME ip so they share one bucket.
        settings.TRUSTED_PROXY_COUNT = 1
        ips = {
            client_ip(_request(xff=f"{spoof}, 198.51.100.7"))
            for spoof in ("1.1.1.1", "2.2.2.2", "9.9.9.9, 8.8.8.8")
        }
        assert ips == {"198.51.100.7"}

    def test_two_trusted_proxies(self, settings):
        # Two chained proxies each append the IP of the connection they
        # received: outer proxy appends the client, inner proxy appends the
        # outer proxy. XFF = "<client>, <outer-proxy>"; the real client is at
        # index len - trusted.
        settings.TRUSTED_PROXY_COUNT = 2
        request = _request(xff="198.51.100.7, 172.16.0.1")
        assert client_ip(request) == "198.51.100.7"

    def test_two_trusted_proxies_ignores_spoofed_prefix(self, settings):
        settings.TRUSTED_PROXY_COUNT = 2
        request = _request(xff="1.2.3.4, 198.51.100.7, 172.16.0.1")
        assert client_ip(request) == "198.51.100.7"

    def test_xff_shorter_than_trusted_count_falls_back(self, settings):
        # XFF has fewer hops than the configured trusted-proxy count (a request
        # that bypassed a proxy, or a misconfig). We must NOT let an
        # attacker-supplied value through; fall back to REMOTE_ADDR.
        settings.TRUSTED_PROXY_COUNT = 2
        request = _request(xff="1.2.3.4", remote_addr="10.9.9.9")
        assert client_ip(request) == "10.9.9.9"

    def test_handles_extra_whitespace_and_empty_entries(self, settings):
        settings.TRUSTED_PROXY_COUNT = 1
        request = _request(xff=" 1.2.3.4 ,  198.51.100.7 ")
        assert client_ip(request) == "198.51.100.7"

    def test_zero_trusted_proxies_falls_back_without_crashing(self, settings):
        # TRUSTED_PROXY_COUNT=0 means "trust no hop" — idx lands at len(hops),
        # which must fall back to REMOTE_ADDR, not raise IndexError.
        settings.TRUSTED_PROXY_COUNT = 0
        request = _request(xff="1.2.3.4, 198.51.100.7", remote_addr="10.9.9.9")
        assert client_ip(request) == "10.9.9.9"
