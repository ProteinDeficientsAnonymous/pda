from datetime import timedelta

import pytest
from audit.models import AuditLogEntry
from community.join_requests import check_in_promotion
from community.models import (
    AttendanceStatus,
    EventType,
    JoinRequest,
    JoinRequestStatus,
    MemberRestoredEmailTemplate,
    WhatsAppLinkConfig,
)
from django.utils import timezone
from notifications.models import Notification, NotificationType
from users.models import User
from users.roles import Role

from tests._auth import auth_headers_for
from tests._events import make_event, make_rsvp


@pytest.fixture
def host(db):
    return User.objects.create_user(phone_number="+12025557100", first_name="Host")


@pytest.fixture
def paused(db):
    user = User.objects.create_user(
        phone_number="+12025557101", first_name="Paused", email="paused@example.com"
    )
    user.roles.clear()
    user.attendance_paused_at = timezone.now() - timedelta(days=10)
    user.attendance_grace_notified_at = timezone.now() - timedelta(days=20)
    user.is_member = False
    user.save(update_fields=["attendance_paused_at", "attendance_grace_notified_at", "is_member"])
    return user


def _attended(user, *, event_type=EventType.OFFICIAL, days_ago=30):
    event = make_event(
        event_type=event_type, start_datetime=timezone.now() - timedelta(days=days_ago)
    )
    make_rsvp(event, user, attendance=AttendanceStatus.ATTENDED)


def _tentative_request(user) -> JoinRequest:
    return JoinRequest.objects.create(
        phone_number=user.phone_number, user=user, status=JoinRequestStatus.TENTATIVE
    )


def _check_in(api_client, host, user, *, event_type=EventType.OFFICIAL, for_plus_one=False):
    event = make_event(
        event_type=event_type, start_datetime=timezone.now() - timedelta(hours=1), created_by=host
    )
    make_rsvp(event, user, has_plus_one=for_plus_one)
    resp = api_client.post(
        f"/api/community/events/{event.id}/rsvps/{user.pk}/attendance/",
        {"attendance": AttendanceStatus.ATTENDED, "for_plus_one": for_plus_one},
        content_type="application/json",
        **auth_headers_for(host),
    )
    assert resp.status_code == 200
    user.refresh_from_db()


@pytest.mark.django_db
class TestRestoreOnCheckIn:
    def test_first_qualifying_check_in_does_not_restore(self, api_client, host, paused):
        _check_in(api_client, host, paused)
        assert paused.attendance_paused_at is not None
        assert paused.is_member is False

    def test_second_qualifying_check_in_restores(
        self, api_client, host, paused, django_capture_on_commit_callbacks
    ):
        _attended(paused, event_type=EventType.CLUB)
        with django_capture_on_commit_callbacks(execute=True):
            _check_in(api_client, host, paused)
        assert paused.attendance_paused_at is None
        assert paused.attendance_grace_notified_at is None
        assert paused.restored_at is not None
        assert paused.is_member is True
        assert (
            paused.roles.filter(name="member").exists()
            == Role.objects.filter(name="member", is_default=True).exists()
        )
        assert AuditLogEntry.objects.filter(
            action="user_attendance_restored", target_id=str(paused.pk)
        ).exists()

    def test_qualifying_event_older_than_a_year_does_not_count(self, api_client, host, paused):
        _attended(paused, days_ago=400)
        _check_in(api_client, host, paused)
        assert paused.attendance_paused_at is not None

    def test_community_event_check_in_never_restores(self, api_client, host, paused):
        _attended(paused)
        _attended(paused)
        _check_in(api_client, host, paused, event_type=EventType.COMMUNITY)
        assert paused.attendance_paused_at is not None

    def test_plus_one_check_in_never_restores(self, api_client, host, paused):
        _attended(paused)
        _attended(paused)
        _check_in(api_client, host, paused, for_plus_one=True)
        assert paused.attendance_paused_at is not None

    def test_host_marking_themselves_never_restores(self, api_client, paused):
        _attended(paused)
        _check_in(api_client, paused, paused)
        assert paused.attendance_paused_at is not None

    def test_host_marking_themselves_never_promotes(self, api_client, paused):
        User.objects.filter(pk=paused.pk).update(attendance_paused_at=None)
        _tentative_request(paused)
        _check_in(api_client, paused, paused)
        assert paused.is_member is False

    def test_stale_tentative_request_does_not_promote_on_first(self, api_client, host, paused):
        jr = _tentative_request(paused)
        _check_in(api_client, host, paused)
        assert paused.is_member is False
        jr.refresh_from_db()
        assert jr.status == JoinRequestStatus.TENTATIVE


@pytest.mark.django_db
class TestRestoreEmail:
    def _restore(self, api_client, host, paused):
        _attended(paused)
        _check_in(api_client, host, paused)

    def test_emails_the_template_with_name_and_whatsapp_link(
        self, api_client, host, paused, fake_email_sender
    ):
        WhatsAppLinkConfig.objects.update_or_create(pk=1, defaults={"link": "https://wa.me/x"})
        MemberRestoredEmailTemplate.objects.update_or_create(
            pk=1, defaults={"body": "hey ${FIRST_NAME}, rejoin: ${WHATSAPP_LINK}"}
        )
        self._restore(api_client, host, paused)

        kwargs = fake_email_sender.send.call_args.kwargs
        assert kwargs["to"] == "paused@example.com"
        assert "welcome back" in kwargs["subject"]
        assert "hey Paused, rejoin: https://wa.me/x" in kwargs["text"]

    def test_default_body_includes_whatsapp_link(self, api_client, host, paused, fake_email_sender):
        WhatsAppLinkConfig.objects.update_or_create(pk=1, defaults={"link": "https://wa.me/x"})
        self._restore(api_client, host, paused)
        assert "https://wa.me/x" in fake_email_sender.send.call_args.kwargs["text"]

    def test_failed_email_keeps_the_restore(self, api_client, host, paused, fake_email_sender):
        fake_email_sender.send.side_effect = RuntimeError("smtp down")
        self._restore(api_client, host, paused)
        assert paused.attendance_paused_at is None

    def test_failed_template_lookup_keeps_the_restore(self, api_client, host, paused, monkeypatch):
        monkeypatch.setattr(MemberRestoredEmailTemplate, "get", classmethod(lambda cls: 1 / 0))
        self._restore(api_client, host, paused)
        assert paused.attendance_paused_at is None

    def test_no_email_without_a_restore(self, api_client, host, paused, fake_email_sender):
        _check_in(api_client, host, paused)
        fake_email_sender.send.assert_not_called()


@pytest.mark.django_db
class TestRestoreNotification:
    def test_notifies_approvers(self, api_client, host, paused, vettor_user):
        _attended(paused)
        _check_in(api_client, host, paused)

        notification = Notification.objects.get(notification_type=NotificationType.MEMBER_RESTORED)
        assert notification.recipient == vettor_user
        assert notification.related_user == paused

    def test_approver_who_checked_them_in_is_not_notified(self, api_client, paused, vettor_user):
        _attended(paused)
        _check_in(api_client, vettor_user, paused)
        assert paused.attendance_paused_at is None
        assert not Notification.objects.filter(recipient=vettor_user).exists()

    def test_no_notification_without_a_restore(self, api_client, host, paused, vettor_user):
        _check_in(api_client, host, paused)
        assert not Notification.objects.filter(recipient=vettor_user).exists()

    def test_failed_notification_keeps_the_restore(
        self, api_client, host, paused, monkeypatch, caplog
    ):
        def boom(*_):
            raise RuntimeError("db hiccup")

        monkeypatch.setattr(check_in_promotion, "create_member_restored_notifications", boom)
        _attended(paused)
        _check_in(api_client, host, paused)
        assert paused.attendance_paused_at is None
        assert "member_restored_notifications_failed" in caplog.text
