from collections.abc import Callable
from itertools import count

from django.db import connection
from django.test.utils import CaptureQueriesContext
from ninja_jwt.tokens import RefreshToken
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

_phones = count(1)


def make_user(name: str = "Person", **extra) -> User:
    return User.objects.create_user(
        phone_number=f"+1312555{next(_phones):04d}",
        password="Testpass123!",
        first_name=name,
        last_name="Last",
        **extra,
    )


def make_user_with(*permissions: PermissionKey) -> User:
    user = make_user("Admin", is_member=True)
    user.roles.add(Role.objects.create(name=f"qc-{user.phone_number}", permissions=permissions))
    return user


def headers_for(user: User) -> dict:
    return {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(user).access_token}"}


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
