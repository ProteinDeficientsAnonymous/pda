"""Tests for the event text-blast send/list/detail endpoints (issue #403).

The inbound Twilio webhook tests live in `test_event_blasts_webhook.py` to
keep both files under the 500-line cap. Twilio API calls are mocked at
`community._sms.send_sms` — no real network requests.
"""

from unittest.mock import patch

import pytest
from community.models import (
    EventBlastMute,
    EventRSVP,
    EventStatus,
    EventTextBlast,
    EventTextBlastDelivery,
    EventTextBlastDeliveryStatus,
    RSVPStatus,
)
from notifications.models import Notification, NotificationType

from tests._event_blasts_shared import auth_headers, make_event, send_blast


@pytest.mark.django_db
class TestSendBlast:
    def test_creator_can_send_to_attending(
        self, api_client, creator, event_with_attendees, attendee, mock_send_sms
    ):
        response = send_blast(
            api_client,
            creator,
            event_with_attendees,
            message="hey see you tonight",
            recipient_filters=["attending"],
        )
        assert response.status_code == 200, response.content
        data = response.json()
        assert data["recipient_count"] == 1
        assert len(data["deliveries"]) == 1
        assert data["deliveries"][0]["status"] == "sent"
        # Twilio called with the composed body (incl. mute suffix + from-line).
        mock_send_sms.assert_called_once()
        sent_to, sent_body = mock_send_sms.call_args.args
        assert sent_to == attendee.phone_number
        assert "hey see you tonight" in sent_body
        assert "reply M to mute" in sent_body
        assert "pda · Creator:" in sent_body

    def test_cohost_can_send(self, api_client, cohost, event_with_attendees, mock_send_sms):
        response = send_blast(
            api_client,
            cohost,
            event_with_attendees,
            message="hi",
            recipient_filters=["attending"],
        )
        assert response.status_code == 200

    def test_stranger_cannot_send(self, api_client, stranger, event_with_attendees, mock_send_sms):
        response = send_blast(
            api_client,
            stranger,
            event_with_attendees,
            message="hi",
            recipient_filters=["attending"],
        )
        assert response.status_code == 403
        assert response.json()["detail"][0]["code"] == "text_blast.not_host"
        mock_send_sms.assert_not_called()

    def test_cancelled_event_rejected(
        self, api_client, creator, event_with_attendees, mock_send_sms
    ):
        event_with_attendees.status = EventStatus.CANCELLED
        event_with_attendees.save()
        response = send_blast(
            api_client,
            creator,
            event_with_attendees,
            message="hi",
            recipient_filters=["attending"],
        )
        assert response.status_code == 400
        assert response.json()["detail"][0]["code"] == "text_blast.event_cancelled"

    def test_invalid_filter_rejected(
        self, api_client, creator, event_with_attendees, mock_send_sms
    ):
        response = send_blast(
            api_client,
            creator,
            event_with_attendees,
            message="hi",
            recipient_filters=["bogus"],
        )
        assert response.status_code == 422
        assert response.json()["detail"][0]["code"] == "text_blast.invalid_filter"

    def test_no_recipients_rejected(self, api_client, creator, mock_send_sms):
        # Event with no attendees + waitlisted filter → empty set.
        event = make_event(creator)
        response = send_blast(
            api_client,
            creator,
            event,
            message="hi",
            recipient_filters=["waitlisted"],
        )
        assert response.status_code == 400
        assert response.json()["detail"][0]["code"] == "text_blast.no_recipients"

    def test_excludes_sender_from_recipients(
        self, api_client, creator, event_with_attendees, mock_send_sms
    ):
        # Creator RSVPs attending to their own event — shouldn't text themselves.
        EventRSVP.objects.create(
            event=event_with_attendees, user=creator, status=RSVPStatus.ATTENDING
        )
        response = send_blast(
            api_client,
            creator,
            event_with_attendees,
            message="hi",
            recipient_filters=["attending"],
        )
        assert response.status_code == 200
        sent_to_phones = {call.args[0] for call in mock_send_sms.call_args_list}
        assert creator.phone_number not in sent_to_phones

    def test_excludes_muted_users(
        self, api_client, creator, event_with_attendees, attendee, mock_send_sms
    ):
        EventBlastMute.objects.create(event=event_with_attendees, user=attendee)
        response = send_blast(
            api_client,
            creator,
            event_with_attendees,
            message="hi",
            recipient_filters=["attending"],
        )
        # Attendee was the only one with attending status; muted → no recipients.
        assert response.status_code == 400
        assert response.json()["detail"][0]["code"] == "text_blast.no_recipients"
        mock_send_sms.assert_not_called()

    def test_combination_filters_dedupe(
        self, api_client, creator, event_with_attendees, mock_send_sms
    ):
        response = send_blast(
            api_client,
            creator,
            event_with_attendees,
            message="hi",
            recipient_filters=["attending", "maybe"],
        )
        assert response.status_code == 200
        assert response.json()["recipient_count"] == 2
        sent_to = {call.args[0] for call in mock_send_sms.call_args_list}
        # Both the attending and maybe users from the fixture.
        assert sent_to == {"+12025550403", "+12025550404"}

    def test_partial_failure_marks_delivery_and_notifies_sender(
        self, api_client, creator, event_with_attendees, attendee, maybe_attendee
    ):
        # Make Twilio fail on the second recipient.
        with patch("community._sms.send_sms") as send_sms:
            send_sms.side_effect = ["SM_ok", Exception("twilio bad recipient")]
            response = send_blast(
                api_client,
                creator,
                event_with_attendees,
                message="hi",
                recipient_filters=["attending", "maybe"],
            )
        assert response.status_code == 200
        deliveries = list(
            EventTextBlastDelivery.objects.filter(blast__event=event_with_attendees).order_by(
                "created_at"
            )
        )
        statuses = sorted(d.status for d in deliveries)
        assert statuses == [
            EventTextBlastDeliveryStatus.FAILED,
            EventTextBlastDeliveryStatus.SENT,
        ]
        # Failure notification fired for the sender.
        notif = Notification.objects.get(
            recipient=creator, notification_type=NotificationType.TEXT_BLAST_FAILURES
        )
        assert "1 person" in notif.message

    def test_lifetime_cap_blocks_sixth_blast(
        self, api_client, creator, event_with_attendees, mock_send_sms
    ):
        # Pre-create 5 blasts the slow way (skipping the endpoint to not trip
        # the rate limit and to avoid stub'ing send_sms 5x).
        for _ in range(5):
            EventTextBlast.objects.create(
                event=event_with_attendees,
                sender=creator,
                message="prior",
                recipient_filters=["attending"],
                recipient_count=1,
            )
        response = send_blast(
            api_client,
            creator,
            event_with_attendees,
            message="6th",
            recipient_filters=["attending"],
        )
        assert response.status_code == 400
        body = response.json()
        assert body["detail"][0]["code"] == "text_blast.event_limit_reached"
        assert body["detail"][0]["params"]["limit"] == 5
        mock_send_sms.assert_not_called()

    def test_lifetime_cap_counts_across_all_hosts(
        self,
        api_client,
        creator,
        cohost,
        event_with_attendees,
        mock_send_sms,
    ):
        # Creator + cohost each pre-create a few; total reaches 5.
        for _ in range(3):
            EventTextBlast.objects.create(
                event=event_with_attendees,
                sender=creator,
                message="x",
                recipient_filters=["attending"],
                recipient_count=1,
            )
        for _ in range(2):
            EventTextBlast.objects.create(
                event=event_with_attendees,
                sender=cohost,
                message="x",
                recipient_filters=["attending"],
                recipient_count=1,
            )
        response = send_blast(
            api_client,
            cohost,
            event_with_attendees,
            message="6th",
            recipient_filters=["attending"],
        )
        assert response.status_code == 400
        assert response.json()["detail"][0]["code"] == "text_blast.event_limit_reached"


@pytest.mark.django_db
class TestListBlasts:
    def test_creator_sees_history(self, api_client, creator, event_with_attendees, mock_send_sms):
        send_blast(
            api_client,
            creator,
            event_with_attendees,
            message="first",
            recipient_filters=["attending"],
        )
        response = api_client.get(
            f"/api/community/events/{event_with_attendees.id}/text-blasts/",
            **auth_headers(creator),
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["blasts"]) == 1
        assert data["blasts_remaining"] == 4
        # List view omits per-recipient deliveries.
        assert data["blasts"][0]["deliveries"] == []

    def test_stranger_cannot_list(self, api_client, stranger, event_with_attendees):
        response = api_client.get(
            f"/api/community/events/{event_with_attendees.id}/text-blasts/",
            **auth_headers(stranger),
        )
        assert response.status_code == 403


@pytest.mark.django_db
class TestBlastDetail:
    def test_detail_returns_masked_phones(
        self, api_client, creator, event_with_attendees, mock_send_sms
    ):
        send = send_blast(
            api_client,
            creator,
            event_with_attendees,
            message="x",
            recipient_filters=["attending"],
        )
        blast_id = send.json()["id"]
        response = api_client.get(
            f"/api/community/events/{event_with_attendees.id}/text-blasts/{blast_id}/",
            **auth_headers(creator),
        )
        assert response.status_code == 200
        delivery = response.json()["deliveries"][0]
        # Phone is masked: `•••XXXX`.
        assert delivery["phone_number_masked"].startswith("•••")
        assert delivery["phone_number_masked"].endswith("0403")
