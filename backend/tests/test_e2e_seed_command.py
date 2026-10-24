import json
from datetime import UTC, datetime

import pytest
from community._attendance_analytics import (
    compute_member_stats,
    is_compliant,
    is_pause_candidate,
    user_rsvps_for_attendance,
)
from community.management.commands.e2e_seed import _month_end
from community.models import (
    AttendanceStatus,
    Document,
    Event,
    EventRSVP,
    JoinRequest,
    RSVPStatus,
    Survey,
)
from django.core.management import call_command
from django.core.management.base import CommandError
from ninja_jwt.tokens import RefreshToken
from users.models import NonMemberRsvpToken, User
from users.permissions import PermissionKey


@pytest.mark.django_db
def test_e2e_seed_member(capsys):
    call_command("e2e_seed", "member")
    out = json.loads(capsys.readouterr().out)
    assert Event.objects.filter(id=out["event_id"]).exists()
    user = User.objects.get(phone_number=out["user_phone"])
    assert user.is_member is True
    assert user.has_seen_veganniversary is True
    assert user.check_password(out["user_password"])
    assert out["access_token"]


@pytest.mark.django_db
def test_e2e_seed_public_new(capsys):
    call_command("e2e_seed", "public-new")
    out = json.loads(capsys.readouterr().out)
    assert Event.objects.filter(id=out["event_id"]).exists()
    assert set(out.keys()) == {"event_id", "event_title", "event_location"}


@pytest.mark.django_db
def test_e2e_seed_public_returning(capsys):
    call_command("e2e_seed", "public-returning")
    out = json.loads(capsys.readouterr().out)
    user = User.objects.get(phone_number=out["user_phone"])
    assert EventRSVP.objects.filter(event_id=out["event_id"], user=user).exists()
    assert NonMemberRsvpToken.resolve_user(out["rsvp_token"]) == user


@pytest.mark.django_db
def test_e2e_seed_comments(capsys):
    call_command("e2e_seed", "comments")
    out = json.loads(capsys.readouterr().out)
    assert NonMemberRsvpToken.resolve_user(out["rsvp_token"]) is not None
    assert EventRSVP.objects.filter(event_id=out["event_id"]).exists()


@pytest.mark.django_db
def test_e2e_seed_my_rsvps(capsys):
    call_command("e2e_seed", "my-rsvps")
    out = json.loads(capsys.readouterr().out)
    assert NonMemberRsvpToken.resolve_user(out["rsvp_token"]) is not None


@pytest.mark.django_db
def test_e2e_seed_live_updates(capsys):
    call_command("e2e_seed", "live-updates")
    out = json.loads(capsys.readouterr().out)
    for key in ("user_a_phone", "user_a_password", "user_b_phone", "user_b_password"):
        assert out[key]
    user_a = User.objects.get(phone_number=out["user_a_phone"])
    assert user_a.is_member is True
    assert user_a.has_seen_veganniversary is True
    user_b = User.objects.get(phone_number=out["user_b_phone"])
    assert user_b.is_member is True
    assert EventRSVP.objects.filter(event_id=out["event_id"], user=user_b).exists()


@pytest.mark.django_db
def test_e2e_seed_member_screens_fixed_copy(capsys):
    call_command("e2e_seed", "member-screens")
    out = json.loads(capsys.readouterr().out)
    seed = User.objects.get(phone_number="+17025550002")
    assert seed.first_name == "Seed"
    assert seed.last_name == "Member"
    assert seed.email == "member@pda.test"
    assert seed.bio == "vegan six years, big into potlucks and mutual aid."
    assert (seed.birthday_month, seed.birthday_day, seed.birthday_year) == (6, 15, 1990)
    assert seed.has_seen_veganniversary is True
    assert (seed.veganniversary_month, seed.veganniversary_day, seed.veganniversary_year) == (
        6,
        None,
        2020,
    )
    assert seed.guidelines_consent_at is not None
    jamie = User.objects.get(phone_number="+17025550003")
    assert jamie.first_name == "Jamie"
    assert jamie.last_name == "Okafor"
    assert jamie.email == "jamie@pda.test"
    assert (jamie.birthday_month, jamie.birthday_day, jamie.birthday_year) == (3, 2, 1991)
    assert out["jamie_id"] == str(jamie.id)
    ash = User.objects.get(phone_number="+17025550004")
    assert ash.first_name == "Ash"
    assert ash.last_name == "Smith"
    assert ash.email in (None, "")
    assert ash.needs_onboarding is True
    assert "potluck" in out["digest_html"]
    assert "see the full calendar" in out["digest_html"]
    event = Event.objects.get(slug="potluck")
    assert event.title == "potluck"
    question = event.rsvp_questions.get()
    assert len(question.label) > 200
    assert question.required is True
    assert event.location == "the park"
    assert out["event_id"] == str(event.id)
    assert EventRSVP.objects.filter(event=event, user=seed).exists()
    guest = User.objects.get(phone_number="+17025550005")
    assert guest.first_name == "River"
    assert guest.is_member is False
    assert EventRSVP.objects.filter(event=event, user=guest).exists()
    assert out["guest_token"]
    call_command("e2e_seed", "member-screens")
    assert User.objects.filter(phone_number="+17025550002").count() == 1
    assert Event.objects.filter(slug="potluck").count() == 1


@pytest.mark.django_db
def test_e2e_seed_member_screens_host_admin_and_gates(capsys):
    call_command("e2e_seed", "member-screens")
    out = json.loads(capsys.readouterr().out)
    hike = Event.objects.get(slug="hike")
    assert out["hike_id"] == str(hike.id)
    picnic = Event.objects.get(slug="picnic")
    assert picnic.status == "cancelled"
    ada = User.objects.get(phone_number="+17025550006")
    assert ada.first_name == "Ada"
    assert ada.roles.filter(name="admin", is_default=True).exists()
    assert out["admin_phone"] == ada.phone_number
    remy = User.objects.get(phone_number="+17025550008")
    assert remy.needs_password_reset is True
    assert out["reset_phone"] == remy.phone_number
    casey = User.objects.get(phone_number="+17025550009")
    assert casey.guidelines_consent_at is None
    assert out["consent_phone"] == casey.phone_number
    survey = Survey.objects.get(slug="potluck-feedback")
    assert survey.created_at == datetime(2026, 6, 1, 18, 0, tzinfo=UTC)
    assert out["survey_id"] == str(survey.id)
    assert JoinRequest.objects.get(phone_number="+17025550007").submitted_at == datetime(
        2026, 6, 1, 18, 0, tzinfo=UTC
    )
    assert out["doc_id"] == str(Document.objects.get(title="house rules").id)
    call_command("e2e_seed", "member-screens")
    assert Event.objects.filter(slug="hike").count() == 1
    assert Event.objects.filter(slug="picnic").count() == 1


def test_month_end_in_january_uses_prior_december():

    now = datetime(2026, 1, 4, 12, 0, tzinfo=UTC)
    assert _month_end(now) == datetime(2026, 1, 31, 22, 0, tzinfo=UTC)
    assert _month_end(now, months_ago=1) == datetime(2025, 12, 31, 22, 0, tzinfo=UTC)


@pytest.mark.django_db
def test_e2e_seed_member_screens_events_use_month_end(capsys, monkeypatch):
    frozen = datetime(2026, 10, 11, 15, 0, tzinfo=UTC)
    monkeypatch.setattr(
        "community.management.commands.e2e_seed.timezone.now",
        lambda: frozen,
    )
    call_command("e2e_seed", "member-screens")
    out = json.loads(capsys.readouterr().out)
    assert Event.objects.get(slug="potluck").start_datetime == datetime(
        2026, 10, 31, 22, 0, tzinfo=UTC
    )
    assert Event.objects.get(slug="hike").start_datetime == datetime(2026, 9, 30, 22, 0, tzinfo=UTC)
    assert Event.objects.get(slug="picnic").start_datetime == datetime(
        2026, 10, 31, 22, 0, tzinfo=UTC
    )
    assert out["calendar_date"] == "2026-10-31"
    assert "october 31" in out["digest_html"]


@pytest.mark.django_db
def test_e2e_seed_attendance_report_buckets_each_rsvp(capsys):
    call_command("e2e_seed", "attendance-report")
    out = json.loads(capsys.readouterr().out)
    event = Event.objects.get(id=out["event_id"])
    host = User.objects.get(id=RefreshToken(out["refresh_token"])["user_id"])
    assert event.created_by == host
    assert not host.roles.exists()
    marks = {r.user.full_name: (r.status, r.attendance) for r in event.rsvps.select_related("user")}
    assert marks == {
        out["attended_name"]: (RSVPStatus.ATTENDING, AttendanceStatus.ATTENDED),
        out["no_show_name"]: (RSVPStatus.ATTENDING, AttendanceStatus.DIDNT_GO),
        out["canceled_name"]: (RSVPStatus.CANT_GO, AttendanceStatus.UNKNOWN),
    }


@pytest.mark.django_db
def test_e2e_seed_attendance_analytics_compliant_and_at_risk(capsys):
    call_command("e2e_seed", "attendance-analytics")
    out = json.loads(capsys.readouterr().out)
    admin = User.objects.get(id=RefreshToken(out["refresh_token"])["user_id"])
    assert admin.has_permission(PermissionKey.MANAGE_EVENTS)
    assert admin.has_permission(PermissionKey.MANAGE_USERS)
    members = User.objects.filter(first_name__icontains=out["search"])
    stats = {
        u.full_name.lower(): compute_member_stats(user_rsvps_for_attendance(u)) for u in members
    }
    assert is_compliant(stats[out["compliant_name"]])
    assert is_pause_candidate(stats[out["at_risk_name"]])
    assert out["at_risk_name"] > out["compliant_name"]


@pytest.mark.django_db
def test_e2e_seed_waitlist_screens_is_rerunnable(capsys):
    call_command("e2e_seed", "waitlist-screens")
    capsys.readouterr()
    call_command("e2e_seed", "waitlist-screens")
    out = json.loads(capsys.readouterr().out)
    event = Event.objects.get(slug="supper")
    assert event.max_attendees == 1
    assert event.allow_plus_ones is True
    wren = User.objects.get(phone_number=out["wren_phone"])
    assert wren.check_password(out["password"])
    rsvp = EventRSVP.objects.get(event=event, user=wren)
    assert rsvp.status == RSVPStatus.WAITLISTED
    guest = NonMemberRsvpToken.resolve_user(out["guest_token"])
    assert guest is not None
    assert EventRSVP.objects.get(event=event, user=guest).status == RSVPStatus.WAITLISTED


@pytest.mark.django_db
def test_e2e_seed_member_screens_clears_waitlist_screens(capsys):
    call_command("e2e_seed", "waitlist-screens")
    call_command("e2e_seed", "member-screens")
    assert not Event.objects.filter(slug="supper").exists()


@pytest.mark.django_db
def test_e2e_seed_membership_journey_admin_and_event_only(capsys):
    call_command("e2e_seed", "membership-journey")
    out = json.loads(capsys.readouterr().out)
    event = Event.objects.get(id=out["event_id"])
    assert event.location == out["event_location"]
    admin = User.objects.get()
    assert admin.has_permission(PermissionKey.APPROVE_JOIN_REQUESTS)
    assert out["admin_refresh_token"]
    assert not JoinRequest.objects.exists()


@pytest.mark.django_db
def test_e2e_seed_unknown_scenario():
    with pytest.raises(CommandError):
        call_command("e2e_seed", "not-a-real-scenario")
