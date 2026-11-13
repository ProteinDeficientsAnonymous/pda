from tests._auth import auth_headers_for
from tests._users import make_user


def send(api_client, method, url, body=None, headers=None):
    kwargs = {"data": body, "content_type": "application/json"} if body is not None else {}
    return getattr(api_client, method)(url, **kwargs, **(headers or {}))


def headers_for(*permissions):
    return auth_headers_for(make_user(*permissions))
