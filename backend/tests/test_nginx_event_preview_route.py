import re
from pathlib import Path

import pytest

NGINX_TEMPLATE = Path(__file__).resolve().parents[2] / "nginx.conf.template"


def _event_preview_location() -> re.Pattern[str]:
    match = re.search(r'location "~(\^/events/[^"]+)"', NGINX_TEMPLATE.read_text())
    assert match, "event preview location block not found in nginx.conf.template"
    # nginx PCRE spells named groups (?<name>…); Python needs (?P<name>…).
    return re.compile(re.sub(r"\(\?<(?=[A-Za-z_])", "(?P<", match.group(1)))


@pytest.mark.parametrize(
    "path",
    [
        "/events/vegan-potluck",
        "/events/vegan-potluck-2",
        "/events/event",
        "/events/3f2b8c1e-9d4a-4e6b-8a7c-1b2d3e4f5a6b",
    ],
)
def test_unfurl_bots_reach_preview_for_slug_and_uuid_links(path):
    assert _event_preview_location().match(path)


@pytest.mark.parametrize(
    "path",
    [
        "/events/add",
        "/events/mine",
        "/events/manage",
        "/events/vegan-potluck/edit",
        "/events/",
    ],
)
def test_non_detail_event_routes_stay_on_spa(path):
    assert not _event_preview_location().match(path)
