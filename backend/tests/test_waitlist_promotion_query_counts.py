import pytest
from community.models import Event, EventRSVP, RSVPStatus
from community.rsvps.waitlist import promote_from_waitlist
from django.db import connection
from django.test.utils import CaptureQueriesContext
from notifications.models import Notification, NotificationType
from notifications.service import notify_users
from users.models import User

from tests._events import make_event, make_rsvp
from tests._users import make_user


def _waitlisted_event(host: User, waitlisted: int):
    event = make_event(
        title="Capped",
        rsvp_enabled=True,
        allow_plus_ones=True,
        max_attendees=1,
        created_by=host,
    )
    rsvps = [make_rsvp(event, make_user(), RSVPStatus.WAITLISTED) for _ in range(waitlisted)]
    return Event.objects.get(pk=event.pk), rsvps


def _promote_all(event: Event) -> int:
    event.max_attendees = 100
    with CaptureQueriesContext(connection) as ctx:
        promote_from_waitlist(event)
    return len(ctx.captured_queries)


@pytest.mark.django_db
def test_promotion_queries_do_not_grow_with_promoted_guests(test_user):
    small, _ = _waitlisted_event(test_user, 2)
    large, _ = _waitlisted_event(test_user, 8)
    assert _promote_all(small) == _promote_all(large)
    assert EventRSVP.objects.filter(status=RSVPStatus.WAITLISTED).count() == 0


@pytest.mark.django_db
def test_promotion_stamps_rows_and_keeps_line_order(test_user):
    event, rsvps = _waitlisted_event(test_user, 4)
    first, second, third, fourth = rsvps
    EventRSVP.objects.filter(pk=third.pk).update(waitlist_position=0)
    EventRSVP.objects.filter(pk=first.pk).update(has_plus_one=True)
    event.max_attendees = 2

    promoted = promote_from_waitlist(event)

    # third jumps the line; first's +1 party needs two seats and blocks everyone behind it.
    assert promoted == [str(third.user_id)]
    third.refresh_from_db()
    assert third.status == RSVPStatus.ATTENDING
    assert third.waitlist_position is None
    assert third.status_changed_at is not None
    assert third.status_changed_at > third.created_at
    assert set(
        EventRSVP.objects.filter(status=RSVPStatus.WAITLISTED).values_list("pk", flat=True)
    ) == {first.pk, second.pk, fourth.pk}
    assert Notification.objects.filter(
        notification_type=NotificationType.WAITLIST_PROMOTED, recipient_id=third.user_id
    ).exists()


@pytest.mark.django_db
def test_notify_users_pings_everyone_in_one_statement(django_assert_num_queries):
    with django_assert_num_queries(1 if connection.vendor == "postgresql" else 0):
        notify_users(["user-1", "user-2", "user-3"])
