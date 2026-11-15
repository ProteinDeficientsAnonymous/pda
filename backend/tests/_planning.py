from community.models import AssignmentStatus, SlotAssignment

from tests._auth import auth_headers_for
from tests._users import make_user


def send(api_client, method, url, body=None, headers=None):
    kwargs = {"data": body, "content_type": "application/json"} if body is not None else {}
    return getattr(api_client, method)(url, **kwargs, **(headers or {}))


def headers_for(*permissions):
    return auth_headers_for(make_user(*permissions))


def assign(slot, user, status=AssignmentStatus.PROPOSED):
    return SlotAssignment.objects.create(slot=slot, user=user, status=status)


def respond(api_client, assignment, action, actor):
    url = f"/api/community/planning/assignments/{assignment.id}/{action}/"
    return send(api_client, "post", url, headers=auth_headers_for(actor))
