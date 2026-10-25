from datetime import UTC, timedelta

from community.models import Event, EventRSVP, EventStatus, RSVPStatus
from django.utils import timezone
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

from tests._cashapp_helpers import csv_line, make_csv
from tests._payment_helpers import create_paid_event
from tests.test_mcp_events_write import _error, _run


def make_user(phone: str, *permissions: str, first: str = "Pay", last: str = "Admin") -> User:
    user = User.objects.create_user(phone_number=phone, first_name=first, last_name=last)
    if permissions:
        user.roles.add(Role.objects.create(name=f"role-{phone}", permissions=list(permissions)))
    return user


def make_importer() -> User:
    return make_user("+12025557200", PermissionKey.IMPORT_PAYMENTS)


def make_event(creator: User, co_host: User | None = None, **fields) -> Event:
    start = timezone.now() + timedelta(days=2)
    event = create_paid_event(
        created_by=creator, price="$15", start_datetime=start, end_datetime=start, **fields
    )
    Event.objects.filter(pk=event.pk).update(created_at=timezone.now() - timedelta(days=10))
    event.co_hosts.add(creator, *([co_host] if co_host else []))
    return event


def make_draft(creator: User) -> Event:
    return make_event(creator, status=EventStatus.DRAFT)


def add_guest(
    event: Event, n: int, name: str, said_paid: bool = True, plus_one: bool = False
) -> User:
    first, last = name.split()
    user = make_user(f"+1202555730{n}", first=first, last=last)
    EventRSVP.objects.create(
        event=event,
        user=user,
        status=RSVPStatus.ATTENDING,
        has_plus_one=plus_one,
        paid_confirmed_at=timezone.now() if said_paid else None,
    )
    return user


def make_guests(event: Event) -> dict[str, User]:
    return {
        "alex": add_guest(event, 1, "Alex Kim"),
        "sam": add_guest(event, 2, "Sam Lee"),
        "jo": add_guest(event, 3, "Jo Park", said_paid=False),
        "riley": add_guest(event, 4, "Riley Chen"),
        "casey": add_guest(event, 5, "Casey Wu", said_paid=False),
    }


def payment_date() -> str:
    return (timezone.now() - timedelta(days=1)).astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")


def make_csv_text(*extra_lines: str) -> str:
    date = payment_date()
    return make_csv(
        csv_line(tx="tx1", date=date, name="Alex Kim"),
        csv_line(tx="tx2", date=date, name="Pat Smith", amount="$30", note="sam lee and jo park"),
        csv_line(tx="tx3", date=date, name="Nobody Here"),
        csv_line(tx="tx4", date=date, name="Morgan Fox", note="for riley"),
        *extra_lines,
    )


def review(user: User, event: Event, csv_text: str) -> dict:
    return _run(user, "review_cashapp_payments", event=str(event.pk), csv_text=csv_text)


def review_refused(user: User, event_ref: str, csv_text: str) -> str:
    return _error(user, "review_cashapp_payments", event=event_ref, csv_text=csv_text)


def verified_ids(event: Event) -> set[str]:
    rows = EventRSVP.objects.filter(event=event, payment_verified_at__isnull=False)
    return {str(uid) for uid in rows.values_list("user_id", flat=True)}
