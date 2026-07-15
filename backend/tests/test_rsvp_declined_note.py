import pytest
from community.models import Event
from notifications.models import Notification, NotificationType
from notifications.service import notify_rsvp_declined_note
from users.models import User

from tests.conftest import future_iso


@pytest.mark.django_db
class TestNotifyRsvpDeclinedNote:
    def _event(self, host):
        return Event.objects.create(
            title="Party",
            start_datetime=future_iso(days=10),
            created_by=host,
        )

    def test_notifies_host(self, test_user, db):
        decliner = User.objects.create_user(
            phone_number="+12025550808",
            password="pw",
            first_name="Decliner",
            last_name="",
        )
        event = self._event(test_user)
        notify_rsvp_declined_note(event=event, author=decliner, note="out of town, sorry!")
        notifs = Notification.objects.filter(
            recipient=test_user,
            notification_type=NotificationType.RSVP_DECLINED_NOTE,
        )
        assert notifs.count() == 1
        n = notifs.first()
        assert n.event_id == event.id
        assert n.related_user_id == decliner.id
        assert "out of town, sorry!" in n.message

    def test_notifies_cohosts_excludes_author(self, test_user, db):
        cohost = User.objects.create_user(
            phone_number="+12025550809", password="pw", first_name="Cohost", last_name=""
        )
        event = self._event(test_user)
        event.co_hosts.add(cohost)
        # Author is the host themselves — they should NOT notify themselves.
        notify_rsvp_declined_note(event=event, author=test_user, note="hi")
        assert not Notification.objects.filter(
            recipient=test_user, notification_type=NotificationType.RSVP_DECLINED_NOTE
        ).exists()
        assert (
            Notification.objects.filter(
                recipient=cohost, notification_type=NotificationType.RSVP_DECLINED_NOTE
            ).count()
            == 1
        )

    def test_long_note_and_name_truncates_without_dangling_quote(self, test_user, db):
        decliner = User.objects.create_user(
            phone_number="+12025550810",
            password="pw",
            first_name="Alexandra Montgomery-Whitfield",
            last_name="",
        )
        event = self._event(test_user)
        long_note = "x" * 280
        notify_rsvp_declined_note(event=event, author=decliner, note=long_note)
        n = Notification.objects.get(
            recipient=test_user, notification_type=NotificationType.RSVP_DECLINED_NOTE
        )
        assert len(n.message) <= 255
        assert n.message.endswith("”")
