"""Tests for the host email-blast endpoint (issue #499).

Hosts/co-hosts email everyone who RSVP'd to their event. Default audience is
every RSVP status (including ``can't go``). Sends individually so addresses are
never shared; one bad send doesn't abort the batch.
"""

import logging

import pytest
from community._validation import Code
from community.models import Event, EventEmailBlast, EventRSVP, RSVPStatus
from users.permissions import PermissionKey
from users.roles import Role

from tests._asserts import assert_error_code
from tests.conftest import future_iso

BLAST_URL = "/api/community/events/{event_id}/email-blast/"


@pytest.fixture
def host_user(db):
    from users.models import User

    return User.objects.create_user(
        phone_number="+14155550199",
        password="hostpass123",
        display_name="Event Host",
        email="host@example.com",
    )


@pytest.fixture
def host_headers(host_user):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(host_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def other_user(db):
    from users.models import User

    return User.objects.create_user(
        phone_number="+14155550200",
        password="otherpass123",
        display_name="Random Member",
        email="other@example.com",
    )


@pytest.fixture
def other_headers(other_user):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(other_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def event_with_attendees(db, host_user):
    """An event hosted by ``host_user`` with a spread of RSVP statuses.

    - attending_one: has email
    - attending_two: NO email (should be skipped)
    - maybe_member: has email
    - cant_go_member: has email
    """
    from users.models import User

    event = Event.objects.create(
        title="Potluck in the Park",
        description="Bring a dish",
        start_datetime=future_iso(days=10),
        end_datetime=future_iso(days=10, hours=2),
        location="The Park",
        created_by=host_user,
        rsvp_enabled=True,
    )
    attending_one = User.objects.create_user(
        phone_number="+14155550301", password="x", display_name="Attend One", email="a1@example.com"
    )
    attending_two = User.objects.create_user(
        phone_number="+14155550302", password="x", display_name="Attend Two", email=""
    )
    maybe_member = User.objects.create_user(
        phone_number="+14155550303", password="x", display_name="Maybe", email="maybe@example.com"
    )
    cant_go_member = User.objects.create_user(
        phone_number="+14155550304", password="x", display_name="CantGo", email="cant@example.com"
    )
    EventRSVP.objects.create(event=event, user=attending_one, status=RSVPStatus.ATTENDING)
    EventRSVP.objects.create(event=event, user=attending_two, status=RSVPStatus.ATTENDING)
    EventRSVP.objects.create(event=event, user=maybe_member, status=RSVPStatus.MAYBE)
    EventRSVP.objects.create(event=event, user=cant_go_member, status=RSVPStatus.CANT_GO)
    return event


def _payload(**overrides):
    base = {"subject": "schedule update", "message": "we moved to 6pm"}
    base.update(overrides)
    return base


@pytest.mark.django_db
class TestEmailBlastAuth:
    def test_unauthenticated_blocked(self, api_client, event_with_attendees):
        response = api_client.post(
            BLAST_URL.format(event_id=event_with_attendees.id),
            _payload(),
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_non_host_blocked(self, api_client, event_with_attendees, other_headers):
        response = api_client.post(
            BLAST_URL.format(event_id=event_with_attendees.id),
            _payload(),
            content_type="application/json",
            **other_headers,
        )
        assert response.status_code == 403
        assert_error_code(response, Code.Perm.DENIED)

    def test_unknown_event_404(self, api_client, host_headers):
        response = api_client.post(
            BLAST_URL.format(event_id="00000000-0000-0000-0000-000000000000"),
            _payload(),
            content_type="application/json",
            **host_headers,
        )
        assert response.status_code == 404
        assert_error_code(response, Code.Event.NOT_FOUND)

    def test_co_host_can_send(
        self, api_client, event_with_attendees, other_user, other_headers, fake_email_sender
    ):
        event_with_attendees.co_hosts.add(other_user)
        response = api_client.post(
            BLAST_URL.format(event_id=event_with_attendees.id),
            _payload(),
            content_type="application/json",
            **other_headers,
        )
        assert response.status_code == 200

    def test_manage_events_permission_can_send(
        self, api_client, event_with_attendees, fake_email_sender
    ):
        from ninja_jwt.tokens import RefreshToken
        from users.models import User

        manager = User.objects.create_user(
            phone_number="+14155550400",
            password="x",
            display_name="Manager",
            email="mgr@example.com",
        )
        role = Role.objects.create(name="blast_mgr", permissions=[PermissionKey.MANAGE_EVENTS])
        manager.roles.add(role)
        headers = {
            "HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(manager).access_token}"  # type: ignore
        }
        response = api_client.post(
            BLAST_URL.format(event_id=event_with_attendees.id),
            _payload(),
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 200


@pytest.mark.django_db
class TestEmailBlastSending:
    def test_default_audience_includes_cant_go_and_skips_no_email(
        self, api_client, event_with_attendees, host_headers, fake_email_sender
    ):
        response = api_client.post(
            BLAST_URL.format(event_id=event_with_attendees.id),
            _payload(),
            content_type="application/json",
            **host_headers,
        )
        assert response.status_code == 200
        data = response.json()
        # attending_one + maybe + cant_go = 3 sent; attending_two has no email.
        assert data["sent_count"] == 3
        assert data["skipped_no_email_count"] == 1
        assert data["failed_count"] == 0
        # cant_go recipient must be in the send set.
        sent_to = {c.kwargs["to"] for c in fake_email_sender.send.call_args_list}
        assert "cant@example.com" in sent_to
        assert "a1@example.com" in sent_to
        assert "maybe@example.com" in sent_to

    def test_addresses_not_leaked_across_recipients(
        self, api_client, event_with_attendees, host_headers, fake_email_sender
    ):
        api_client.post(
            BLAST_URL.format(event_id=event_with_attendees.id),
            _payload(),
            content_type="application/json",
            **host_headers,
        )
        # Each send targets exactly one recipient — no shared To/BCC list.
        for call in fake_email_sender.send.call_args_list:
            to = call.kwargs["to"]
            assert isinstance(to, str)
            assert "," not in to

    def test_audience_narrowing_filter(
        self, api_client, event_with_attendees, host_headers, fake_email_sender
    ):
        response = api_client.post(
            BLAST_URL.format(event_id=event_with_attendees.id),
            _payload(audience=[RSVPStatus.ATTENDING.value]),
            content_type="application/json",
            **host_headers,
        )
        assert response.status_code == 200
        data = response.json()
        # Only the two attending RSVPs match; one of them has no email.
        assert data["sent_count"] == 1
        assert data["skipped_no_email_count"] == 1
        sent_to = {c.kwargs["to"] for c in fake_email_sender.send.call_args_list}
        assert sent_to == {"a1@example.com"}

    def test_invalid_audience_400(
        self, api_client, event_with_attendees, host_headers, fake_email_sender
    ):
        response = api_client.post(
            BLAST_URL.format(event_id=event_with_attendees.id),
            _payload(audience=["bogus_status"]),
            content_type="application/json",
            **host_headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Event.BLAST_INVALID_AUDIENCE)

    def test_plaintext_body_preserves_special_characters(
        self, api_client, event_with_attendees, host_headers, fake_email_sender
    ):
        # The plaintext alternative must not HTML-escape free-form host text —
        # `&`, `<`, `>` are common in real messages.
        api_client.post(
            BLAST_URL.format(event_id=event_with_attendees.id),
            _payload(message="tom & jerry: 5 < 10"),
            content_type="application/json",
            **host_headers,
        )
        first_call = fake_email_sender.send.call_args_list[0]
        text = first_call.kwargs["text"]
        assert "tom & jerry: 5 < 10" in text
        assert "&amp;" not in text
        # The HTML part, by contrast, must escape it.
        html = first_call.kwargs["html"]
        assert "tom &amp; jerry" in html

    def test_no_recipients_400(self, api_client, host_user, host_headers, fake_email_sender):
        event = Event.objects.create(
            title="Empty Event",
            start_datetime=future_iso(days=5),
            end_datetime=future_iso(days=5, hours=1),
            location="Nowhere",
            created_by=host_user,
            rsvp_enabled=True,
        )
        response = api_client.post(
            BLAST_URL.format(event_id=event.id),
            _payload(),
            content_type="application/json",
            **host_headers,
        )
        assert response.status_code == 400
        assert_error_code(response, Code.Event.BLAST_NO_RECIPIENTS)

    def test_one_send_failure_does_not_abort_batch(
        self, api_client, event_with_attendees, host_headers, fake_email_sender
    ):
        from notifications.email_sender import SendResult

        # First recipient fails, the rest succeed.
        fake_email_sender.send.side_effect = [
            SendResult(success=False, error="bounced"),
            SendResult(success=True, provider_message_id="ok2"),
            SendResult(success=True, provider_message_id="ok3"),
        ]
        response = api_client.post(
            BLAST_URL.format(event_id=event_with_attendees.id),
            _payload(),
            content_type="application/json",
            **host_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["failed_count"] == 1
        assert data["sent_count"] == 2
        # All three eligible recipients were still attempted.
        assert fake_email_sender.send.call_count == 3

    def test_send_exception_counts_as_failure(
        self, api_client, event_with_attendees, host_headers, fake_email_sender
    ):
        from notifications.email_sender import SendResult

        fake_email_sender.send.side_effect = [
            RuntimeError("smtp blew up"),
            SendResult(success=True, provider_message_id="ok2"),
            SendResult(success=True, provider_message_id="ok3"),
        ]
        response = api_client.post(
            BLAST_URL.format(event_id=event_with_attendees.id),
            _payload(),
            content_type="application/json",
            **host_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["failed_count"] == 1
        assert data["sent_count"] == 2


@pytest.mark.django_db
class TestEmailBlastRecordAndAudit:
    def test_blast_record_persisted(
        self, api_client, event_with_attendees, host_user, host_headers, fake_email_sender
    ):
        api_client.post(
            BLAST_URL.format(event_id=event_with_attendees.id),
            _payload(subject="big news", message="read me"),
            content_type="application/json",
            **host_headers,
        )
        blast = EventEmailBlast.objects.get(event=event_with_attendees)
        assert blast.sender_id == host_user.id
        assert blast.subject == "big news"
        assert blast.body == "read me"
        assert blast.recipient_count == 3
        assert blast.skipped_no_email_count == 1
        assert blast.failed_count == 0

    def test_audit_log_written(
        self, api_client, event_with_attendees, host_headers, fake_email_sender
    ):
        # The pda.audit logger has propagate=False, so caplog's root handler
        # never sees it — attach a capturing handler directly to that logger.
        records: list[logging.LogRecord] = []

        class _Capture(logging.Handler):
            def emit(self, record):
                records.append(record)

        audit_logger = logging.getLogger("pda.audit")
        handler = _Capture()
        audit_logger.addHandler(handler)
        try:
            api_client.post(
                BLAST_URL.format(event_id=event_with_attendees.id),
                _payload(),
                content_type="application/json",
                **host_headers,
            )
        finally:
            audit_logger.removeHandler(handler)

        match = next(
            (r for r in records if getattr(r, "action", None) == "event_email_blast_sent"), None
        )
        assert match is not None
        assert match.target_id == str(event_with_attendees.id)
        assert match.details["sent_count"] == 3


@pytest.mark.django_db
class TestEmailBlastValidationAndRateLimit:
    def test_empty_subject_422(
        self, api_client, event_with_attendees, host_headers, fake_email_sender
    ):
        response = api_client.post(
            BLAST_URL.format(event_id=event_with_attendees.id),
            _payload(subject=""),
            content_type="application/json",
            **host_headers,
        )
        assert response.status_code == 422

    def test_empty_message_422(
        self, api_client, event_with_attendees, host_headers, fake_email_sender
    ):
        response = api_client.post(
            BLAST_URL.format(event_id=event_with_attendees.id),
            _payload(message=""),
            content_type="application/json",
            **host_headers,
        )
        assert response.status_code == 422

    def test_oversized_subject_422(
        self, api_client, event_with_attendees, host_headers, fake_email_sender
    ):
        response = api_client.post(
            BLAST_URL.format(event_id=event_with_attendees.id),
            _payload(subject="x" * 151),
            content_type="application/json",
            **host_headers,
        )
        assert response.status_code == 422

    def test_rate_limited_after_five_in_window(
        self, api_client, event_with_attendees, host_headers, fake_email_sender
    ):
        url = BLAST_URL.format(event_id=event_with_attendees.id)
        for _ in range(5):
            ok = api_client.post(url, _payload(), content_type="application/json", **host_headers)
            assert ok.status_code == 200
        sixth = api_client.post(url, _payload(), content_type="application/json", **host_headers)
        assert sixth.status_code == 429
        assert_error_code(sixth, Code.Rate.LIMITED)
