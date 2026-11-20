"""client_ip must key on Railway's edge hop, past internal proxies, never the spoofable left side."""

import asyncio

import pytest
from config import gunicorn_conf
from config.ratelimit import client_ip
from django.test import RequestFactory
from gunicorn.config import validate_string_to_addr_list
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

NGINX = "127.0.0.1"
CLIENT = "198.51.100.7"


def _request(*, xff=None, remote_addr=NGINX):
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

    def test_railway_chain_skips_internal_proxy_hop(self):
        # Observed on staging: nginx's peer is a rotating 100.64.0.x Railway proxy.
        assert client_ip(_request(xff=f"{CLIENT}, 100.64.0.15")) == CLIENT

    def test_rotating_internal_proxies_share_one_bucket(self):
        ips = {client_ip(_request(xff=f"{CLIENT}, 100.64.0.{n}")) for n in range(1, 17)}
        assert ips == {CLIENT}

    def test_distinct_clients_behind_same_proxy_get_distinct_buckets(self):
        a = client_ip(_request(xff="198.51.100.7, 100.64.0.2"))
        b = client_ip(_request(xff="203.0.113.50, 100.64.0.2"))
        assert a != b

    def test_extra_internal_hops_are_skipped(self):
        xff = f"{CLIENT}, 10.1.2.3, 100.64.0.4, 172.16.0.9, 192.168.1.1"
        assert client_ip(_request(xff=xff)) == CLIENT

    @pytest.mark.parametrize("spoof", ["1.1.1.1", "2.2.2.2", "9.9.9.9, 8.8.8.8", "10.0.0.1"])
    def test_spoofed_left_hops_are_ignored(self, spoof):
        # The edge appends the real client after whatever the attacker sent.
        assert client_ip(_request(xff=f"{spoof}, {CLIENT}, 100.64.0.7")) == CLIENT

    def test_spoofed_internal_looking_hop_does_not_hide_client(self):
        # An attacker can't push a private address to the right of the edge's hop.
        assert client_ip(_request(xff=f"100.64.0.1, {CLIENT}, 100.64.0.7")) == CLIENT

    def test_ipv6_client(self):
        assert client_ip(_request(xff="2001:db8::1, 100.64.0.3")) == "2001:db8::1"

    def test_ipv6_internal_hops_are_skipped(self):
        assert client_ip(_request(xff=f"{CLIENT}, fd12::1, ::1")) == CLIENT

    def test_handles_extra_whitespace_and_empty_entries(self):
        assert client_ip(_request(xff=f" 1.2.3.4 ,, {CLIENT} ,100.64.0.1 ")) == CLIENT

    def test_all_internal_hops_falls_back_to_remote_addr(self):
        assert client_ip(_request(xff="100.64.0.1, 10.0.0.2")) == NGINX

    def test_xff_ignored_when_peer_is_public(self):
        # A direct, un-proxied caller fully controls XFF; key on the socket peer.
        request = _request(xff="1.2.3.4", remote_addr="203.0.113.9")
        assert client_ip(request) == "203.0.113.9"

    @pytest.mark.parametrize("peer", ["fd12::5", "10.0.0.8", "100.64.0.2"])
    def test_xff_ignored_when_peer_is_private_network_not_nginx(self, peer):
        # gunicorn binds 0.0.0.0, so a sibling Railway service could set XFF directly.
        assert client_ip(_request(xff=f"1.2.3.4, {CLIENT}", remote_addr=peer)) == peer

    def test_ipv6_loopback_peer_is_trusted(self):
        assert client_ip(_request(xff=f"{CLIENT}, 100.64.0.3", remote_addr="::1")) == CLIENT

    def test_ipv4_mapped_loopback_peer_is_trusted(self):
        request = _request(xff=f"{CLIENT}, 100.64.0.3", remote_addr="::ffff:127.0.0.1")
        assert client_ip(request) == CLIENT

    def test_ipv4_mapped_internal_hops_are_skipped(self):
        assert client_ip(_request(xff=f"{CLIENT}, ::ffff:100.64.0.5, ::ffff:10.0.0.1")) == CLIENT


def test_uvicorn_leaves_nginx_as_the_peer():
    # Otherwise REMOTE_ADDR becomes the 100.64 hop and client_ip never reads XFF.
    seen = {}

    async def app(scope, receive, send):
        seen["client"] = scope["client"]

    trusted = validate_string_to_addr_list(gunicorn_conf.forwarded_allow_ips)
    middleware = ProxyHeadersMiddleware(app, trusted_hosts=trusted)
    headers = [(b"x-forwarded-for", f"{CLIENT}, 100.64.0.7".encode())]
    scope = {"type": "http", "client": (NGINX, 5000), "headers": headers}
    asyncio.run(middleware(scope, None, None))
    assert seen["client"][0] == NGINX
