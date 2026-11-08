import pytest
from community.models import AttendanceStatus, EventRSVP, EventType, RSVPStatus
from django.utils import timezone
from notifications.models import Notification, NotificationType
from tests._events import make_event, make_rsvp
from tests._users import make_user
from users._attendance_pause import apply_attendance_pause

EVENT_TYPES = [EventType.COMMUNITY, EventType.OFFICIAL]
PAID_OR_CHECKED_IN = [
    {"paid_confirmed_at": "now"},
    {"payment_verified_at": "now"},
    {"checked_in_at": "now"},
    {"attendance": AttendanceStatus.ATTENDED},
]


def _fields(mark: dict) -> dict:
    return {k: timezone.now() if v == "now" else v for k, v in mark.items()}


@pytest.mark.django_db
class TestDraftedEventRsvps:
    @pytest.mark.parametrize("event_type", EVENT_TYPES)
    @pytest.mark.parametrize("mark", PAID_OR_CHECKED_IN)
    def test_keeps_paid_or_checked_in_rsvp(self, rf, member, event_type, mark):
        event = make_event(created_by=member, event_type=event_type)
        rsvp = make_rsvp(event, make_user(), **_fields(mark))

        apply_attendance_pause(rf.get("/"), member)

        rsvp.refresh_from_db()
        assert rsvp.status == RSVPStatus.ATTENDING

    @pytest.mark.parametrize("event_type", EVENT_TYPES)
    def test_deletes_unpaid_unchecked_rsvp(self, rf, member, event_type):
        event = make_event(created_by=member, event_type=event_type)
        make_rsvp(event, make_user())

        apply_attendance_pause(rf.get("/"), member)

        assert not EventRSVP.objects.filter(event=event).exists()

    @pytest.mark.parametrize("event_type", EVENT_TYPES)
    def test_notifies_kept_and_removed_guests(
        self, rf, member, event_type, django_capture_on_commit_callbacks
    ):
        event = make_event(created_by=member, event_type=event_type)
        paid, unpaid = make_user(), make_user()
        make_rsvp(event, paid, paid_confirmed_at=timezone.now())
        make_rsvp(event, unpaid)

        with django_capture_on_commit_callbacks(execute=True):
            apply_attendance_pause(rf.get("/"), member)

        notified = Notification.objects.filter(
            notification_type=NotificationType.EVENT_UNPUBLISHED
        ).values_list("recipient_id", flat=True)
        assert set(notified) == {paid.pk, unpaid.pk}

    def test_keeps_own_paid_rsvp_on_drafted_event(self, rf, member):
        event = make_event(created_by=member)
        rsvp = make_rsvp(event, member, paid_confirmed_at=timezone.now())

        apply_attendance_pause(rf.get("/"), member)

        rsvp.refresh_from_db()
        assert rsvp.status == RSVPStatus.ATTENDING
        assert rsvp.cancelled_at is None
