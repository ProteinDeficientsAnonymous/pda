from config.ratelimit import client_ip, rate_limit
from ninja import Router
from pydantic import BaseModel
from users.models import NonMemberRsvpToken, User

from community._event_helpers import _event_out
from community._event_schemas import EventOut
from community._shared import ErrorOut
from community._validation import Code, raise_validation
from community.models import EventType

router = Router()


class MyRsvpsUserOut(BaseModel):
    display_name: str
    email: str
    phone_number: str


class MyRsvpItemOut(BaseModel):
    event: EventOut
    status: str
    has_plus_one: bool


class MyRsvpsOut(BaseModel):
    user: MyRsvpsUserOut
    rsvps: list[MyRsvpItemOut]


def _resolve_token_user(token: str) -> User:
    """Resolve a manage-rsvp token to its non-member user, or 404."""
    user = NonMemberRsvpToken.resolve_user(token)
    if user is None:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    return user


@router.get(
    "/public/my-rsvps/",
    response={200: MyRsvpsOut, 404: ErrorOut, 429: ErrorOut},
    auth=None,
)
@rate_limit(key_func=client_ip, rate="30/h")
def list_my_rsvps(request, token: str = ""):
    user = _resolve_token_user(token)
    rsvps = (
        user.event_rsvps.filter(event__event_type=EventType.OFFICIAL)
        .select_related("event", "event__created_by")
        .prefetch_related("event__co_hosts", "event__invited_users", "event__rsvps__user")
    )
    items = [
        MyRsvpItemOut(
            event=_event_out(rsvp.event, user),
            status=rsvp.status,
            has_plus_one=rsvp.has_plus_one,
        )
        for rsvp in rsvps
    ]
    return 200, MyRsvpsOut(
        user=MyRsvpsUserOut(
            display_name=user.display_name,
            email=user.email or "",
            phone_number=user.phone_number,
        ),
        rsvps=items,
    )
