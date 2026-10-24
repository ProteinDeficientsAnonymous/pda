import re
from pathlib import Path

import pytest

NGINX_TEMPLATE = Path(__file__).resolve().parents[2] / "nginx.conf.template"


def _template() -> str:
    return NGINX_TEMPLATE.read_text()


def _client_ip_pattern() -> re.Pattern[str]:
    match = re.search(r'map \$http_x_forwarded_for \$mcp_client_ip \{[^}]*"~([^"]+)"', _template())
    assert match, "mcp_client_ip map not found in nginx.conf.template"
    return re.compile(match.group(1))


def _location_block(path: str) -> str:
    for match in re.finditer(r"location ([^{]+)\{(.*?)\n    \}", _template(), re.S):
        spec = match.group(1).strip()
        if spec == f"= {path}" or (spec.startswith("~ ") and re.fullmatch(spec[2:].strip(), path)):
            return match.group(2)
    raise AssertionError(f"no location in nginx.conf.template matches {path}")


@pytest.mark.parametrize(
    ("forwarded", "client"),
    [
        ("203.0.113.7", "203.0.113.7"),
        ("1.2.3.4, 203.0.113.7", "203.0.113.7"),
        ("spoofed, also-spoofed, 203.0.113.7 ", "203.0.113.7"),
        ("1.2.3.4,203.0.113.7", "203.0.113.7"),
        ("2001:db8::1", "2001:db8::1"),
    ],
)
def test_rate_limit_keys_on_rightmost_forwarded_hop(forwarded, client):
    match = _client_ip_pattern().search(forwarded)
    assert match
    assert match.group(1) == client


@pytest.mark.parametrize(
    ("path", "zone"),
    [("/register", "mcp_signup"), ("/authorize", "mcp_signup"), ("/token", "mcp_token")],
)
def test_oauth_endpoints_are_rate_limited(path, zone):
    assert f"limit_req zone={zone} " in _location_block(path)


@pytest.mark.parametrize("zone", ["mcp_signup", "mcp_token"])
def test_rate_limit_zones_use_client_ip_key(zone):
    assert re.search(rf"limit_req_zone \$mcp_client_ip zone={zone}:", _template())
