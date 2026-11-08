from collections.abc import Callable

from django.db import connection
from django.test.utils import CaptureQueriesContext


def _capture(client, url: str, headers: dict) -> CaptureQueriesContext:
    with CaptureQueriesContext(connection) as ctx:
        response = client.get(url, **headers)
    assert response.status_code == 200, response.content
    return ctx


def assert_constant_queries(
    client, url: str, grow: Callable[[int], object], headers: dict | None = None
) -> None:
    """Fail if GET url issues more queries after grow() adds rows (an N+1).

    grow(callable): adds n rows to whatever the endpoint lists.
    """
    headers = headers or {}
    grow(2)
    client.get(url, **headers)  # warm one-time caches so they don't skew the small count
    small = _capture(client, url, headers)
    grow(6)
    large = _capture(client, url, headers)
    sql = "\n".join(q["sql"][:160] for q in large.captured_queries)
    assert len(large) == len(small), f"{len(small)} -> {len(large)} queries:\n{sql}"
