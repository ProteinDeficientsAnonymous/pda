from datetime import timedelta

import pytest
from community.models import (
    Event,
    EventRSVP,
    EventStatus,
    EventType,
    JoinRequest,
    JoinRequestStatus,
    RSVPStatus,
    TentativeAttendanceNudge,
)
from django.core.management import call_command
from django.db.models import F
from django.utils import timezone
from notifications.email_sender import SendResult
from users.models import User

NUDGE_SUBJECT = "you're almost in at pda"


def _make_tentative(phone_number: str, *, set_up_days_ago: int = 8, **extra) -> User:
    extra.setdefault("email", f"{phone_number}@example.test")
    extra.setdefault("first_name", "Sprout")
    extra.setdefault("is_member", False)
    extra.setdefault("needs_onboarding", False)
    extra.setdefault("onboarded_at", timezone.now() - timedelta(days=set_up_days_ago))
    user = User.objects.create(phone_number=phone_number, **extra)
    JoinRequest.objects.create(
        first_name="Sprout",
        phone_number=phone_number,
        email=user.email,
        user=user,
        status=JoinRequestStatus.TENTATIVE,
        tentative_at=timezone.now() - timedelta(days=set_up_days_ago),
    )
    return user


def _rsvp(user: User, *, days_from_now: int = 3, **overrides) -> EventRSVP:
    event = Event.objects.create(
        title="potluck",
        event_type=overrides.pop("event_type", EventType.OFFICIAL),
        status=EventStatus.ACTIVE,
        start_datetime=timezone.now() + timedelta(days=days_from_now),
    )
    return EventRSVP.objects.create(
        event=event, user=user, status=overrides.pop("status", RSVPStatus.ATTENDING)
    )


def _nudge_calls(fake_sender) -> list:
    return [c for c in fake_sender.send.call_args_list if c.kwargs["subject"] == NUDGE_SUBJECT]


def _shift_back(user: User, days: int) -> None:
    User.objects.filter(pk=user.pk).update(onboarded_at=F("onboarded_at") - timedelta(days=days))
    TentativeAttendanceNudge.objects.update(sent_at=F("sent_at") - timedelta(days=days))


@pytest.mark.django_db
class TestTentativeAttendanceNudge:
    def test_nudges_tentative_member_a_week_after_setup(self, fake_email_sender):
        user = _make_tentative("+12025550401")
        call_command("send_weekly_digest")
        calls = _nudge_calls(fake_email_sender)
        assert [c.kwargs["to"] for c in calls] == [user.email]
        assert "/calendar" in calls[0].kwargs["text"]
        assert "/settings" in calls[0].kwargs["text"]

    def test_waits_a_week_after_setup(self, fake_email_sender):
        _make_tentative("+12025550402", set_up_days_ago=3)
        call_command("send_weekly_digest")
        assert _nudge_calls(fake_email_sender) == []

    def test_weekly_runs_send_at_one_two_and_four_weeks_then_monthly(self, fake_email_sender):
        user = _make_tentative("+12025550403", set_up_days_ago=0)
        sent_weeks = []
        for week in range(1, 13):
            _shift_back(user, 7)
            before = len(_nudge_calls(fake_email_sender))
            call_command("send_weekly_digest")
            if len(_nudge_calls(fake_email_sender)) > before:
                sent_weeks.append(week)
        assert sent_weeks == [1, 2, 4, 8, 12]
        assert list(
            TentativeAttendanceNudge.objects.order_by("nudge_number").values_list(
                "nudge_number", flat=True
            )
        ) == [1, 2, 3, 4, 5]

    @pytest.mark.parametrize(
        "status", [RSVPStatus.ATTENDING, RSVPStatus.MAYBE, RSVPStatus.WAITLISTED]
    )
    def test_pauses_while_signed_up_for_upcoming_official_event(self, fake_email_sender, status):
        _rsvp(_make_tentative("+12025550404"), status=status)
        call_command("send_weekly_digest")
        assert _nudge_calls(fake_email_sender) == []

    def test_pauses_for_club_event(self, fake_email_sender):
        _rsvp(_make_tentative("+12025550405"), event_type=EventType.CLUB)
        call_command("send_weekly_digest")
        assert _nudge_calls(fake_email_sender) == []

    @pytest.mark.parametrize(
        "overrides",
        [
            {"event_type": EventType.COMMUNITY},
            {"status": RSVPStatus.CANT_GO},
            {"status": RSVPStatus.REMOVED},
            {"days_from_now": -2},
        ],
        ids=["community_event", "cant_go", "removed", "past_event"],
    )
    def test_still_nudges_without_a_live_signup(self, fake_email_sender, overrides):
        _rsvp(_make_tentative("+12025550406"), **overrides)
        call_command("send_weekly_digest")
        assert len(_nudge_calls(fake_email_sender)) == 1

    def test_resumes_after_signed_up_event_passes_without_check_in(self, fake_email_sender):
        user = _make_tentative("+12025550407")
        rsvp = _rsvp(user)
        call_command("send_weekly_digest")
        assert _nudge_calls(fake_email_sender) == []
        Event.objects.filter(pk=rsvp.event_id).update(
            start_datetime=timezone.now() - timedelta(days=1)
        )
        call_command("send_weekly_digest")
        assert len(_nudge_calls(fake_email_sender)) == 1

    @pytest.mark.parametrize(
        "extra",
        [
            {"attendance_nudge_opt_out": True},
            {"needs_onboarding": True, "onboarded_at": None},
            {"archived_at": timezone.now()},
            {"is_paused": True},
            {"is_active": False},
            {"email": ""},
        ],
        ids=["opted_out", "not_set_up", "archived", "paused", "inactive", "no_email"],
    )
    def test_skips_users_who_should_not_be_nudged(self, fake_email_sender, extra):
        _make_tentative("+12025550408", **extra)
        call_command("send_weekly_digest")
        assert _nudge_calls(fake_email_sender) == []

    def test_skips_promoted_member(self, fake_email_sender):
        user = _make_tentative("+12025550409")
        user.is_member = True
        user.save(update_fields=["is_member"])
        user.join_requests.update(status=JoinRequestStatus.APPROVED)
        call_command("send_weekly_digest")
        assert _nudge_calls(fake_email_sender) == []

    def test_falls_back_to_tentative_date_without_onboarded_at(self, fake_email_sender):
        _make_tentative("+12025550410", onboarded_at=None)
        call_command("send_weekly_digest")
        assert len(_nudge_calls(fake_email_sender)) == 1

    def test_rerun_does_not_double_send(self, fake_email_sender):
        _make_tentative("+12025550411")
        call_command("send_weekly_digest")
        call_command("send_weekly_digest")
        assert len(_nudge_calls(fake_email_sender)) == 1

    def test_failed_send_is_retried_next_run(self, fake_email_sender):
        _make_tentative("+12025550412")
        fake_email_sender.send.return_value = SendResult(success=False, error="boom")
        call_command("send_weekly_digest")
        assert not TentativeAttendanceNudge.objects.exists()
        fake_email_sender.send.return_value = SendResult(success=True, provider_message_id="ok")
        call_command("send_weekly_digest")
        assert TentativeAttendanceNudge.objects.get().nudge_number == 1

    def test_test_send_skips_nudges(self, fake_email_sender):
        _make_tentative("+12025550413")
        call_command("send_weekly_digest", to="smoke@example.test")
        assert _nudge_calls(fake_email_sender) == []
