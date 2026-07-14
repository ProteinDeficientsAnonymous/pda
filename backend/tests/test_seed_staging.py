from datetime import timedelta

import pytest
from community.management.commands._seed_staging_data import (
    NON_MEMBER_EVENT_TITLE,
    NON_MEMBER_SPECS,
    OFFICIAL_FULL_TITLE,
    OFFICIAL_PAST_TITLE,
    OFFICIAL_TODAY_TITLE,
    PASSWORD,
    STAGING_EVENTS,
    TOKEN_EXPIRED,
    TOKEN_NONE,
    TOKEN_VALID,
    cond_email,
    cond_phone,
    condition_combinations,
    condition_label,
    is_seed_allowed,
    perm_email,
    perm_phone,
)
from community.models import AttendanceStatus, Event, EventRSVP, EventType, RSVPStatus
from django.contrib.auth.hashers import check_password
from django.core.management import call_command
from django.utils import timezone
from users.models import NonMemberRsvpToken, User
from users.permissions import PermissionKey
from users.roles import Role


def test_password_meets_validators():
    assert len(PASSWORD) >= 8
    assert any(c.islower() for c in PASSWORD)
    assert any(c.isupper() for c in PASSWORD)
    assert not PASSWORD.isdigit()


def test_perm_phone_is_zero_padded_in_own_block():
    assert perm_phone(0) == "+17025550100"
    assert perm_phone(11) == "+17025550111"


def test_cond_phone_is_zero_padded_in_own_block():
    assert cond_phone(0) == "+17025550200"
    assert cond_phone(7) == "+17025550207"


def test_perm_and_cond_blocks_are_disjoint():
    perm = {perm_phone(i) for i in range(len(PermissionKey.values))}
    cond = {cond_phone(i) for i in range(8)}
    assert perm.isdisjoint(cond)
    assert all(not p.startswith("+1702555000") for p in perm | cond)


def test_condition_combinations_are_all_eight_unique():
    combos = condition_combinations()
    assert len(combos) == 8
    assert len(set(combos)) == 8
    assert (True, True, True) in combos
    assert (False, False, False) in combos


def test_condition_label_is_deterministic_and_descriptive():
    assert condition_label((True, True, True)) == "cond: complete"
    label = condition_label((False, True, False))
    assert label.startswith("cond: ")
    assert "no-email" in label
    assert "needs-sms" in label


def test_emails_are_distinct_and_key_derived():
    assert perm_email("manage_events") == "perm.manage_events@staging.example"
    assert cond_email(3) == "cond03@staging.example"


def test_is_seed_allowed_guard():
    assert is_seed_allowed(None, force=False) is True
    assert is_seed_allowed("", force=False) is True
    assert is_seed_allowed("staging", force=False) is True
    assert is_seed_allowed("production", force=False) is False
    assert is_seed_allowed("production", force=True) is True
    assert is_seed_allowed("prod-preview", force=False) is False


def test_staging_events_span_past_current_future():
    deltas = [e.delta_days for e in STAGING_EVENTS]
    assert any(d < 0 for d in deltas)
    assert any(d == 0 for d in deltas)
    assert any(d > 0 for d in deltas)
    assert len(STAGING_EVENTS) >= 8


@pytest.mark.django_db
def test_seed_staging_creates_one_role_per_permission():
    call_command("seed_staging")
    for key in PermissionKey.values:
        role = Role.objects.get(name=f"perm: {key}")
        assert role.permissions == [key]
        assert role.is_default is False


@pytest.mark.django_db
def test_seed_staging_perm_users_hold_only_their_role_and_are_onboarded():
    call_command("seed_staging")
    for index, key in enumerate(PermissionKey.values):
        user = User.objects.get(phone_number=perm_phone(index))
        assert user.is_member is True
        assert user.needs_onboarding is False
        assert user.onboarded_at is not None
        assert check_password(PASSWORD, user.password)
        role_names = set(user.roles.values_list("name", flat=True))
        assert role_names == {f"perm: {key}"}
        assert user.email == perm_email(key)
        assert user.guidelines_consent_at is not None
        assert user.sms_consent_at is not None


@pytest.mark.django_db
def test_seed_staging_creates_eight_member_only_condition_users():
    call_command("seed_staging")
    combos_seen = set()
    for index in range(8):
        user = User.objects.get(phone_number=cond_phone(index))
        assert user.is_member is True
        assert user.needs_onboarding is False
        assert check_password(PASSWORD, user.password)
        role_names = set(user.roles.values_list("name", flat=True))
        assert role_names == {"member"}
        combos_seen.add(
            (
                user.email is not None and user.email != "",
                user.guidelines_consent_at is not None,
                user.sms_consent_at is not None,
            )
        )
    assert combos_seen == set(condition_combinations())


@pytest.mark.django_db
def test_seed_staging_perm_and_condition_users_are_disjoint():
    call_command("seed_staging")
    perm = set(
        User.objects.filter(phone_number__startswith="+170255501").values_list(
            "phone_number", flat=True
        )
    )
    cond = set(
        User.objects.filter(phone_number__startswith="+170255502").values_list(
            "phone_number", flat=True
        )
    )
    assert len(perm) == len(PermissionKey.values)
    assert len(cond) == 8
    assert perm.isdisjoint(cond)


@pytest.mark.django_db
def test_seed_staging_events_span_past_current_future():
    call_command("seed_staging")
    now = timezone.now()
    events = list(Event.objects.filter(title__startswith="[staging] "))
    assert len(events) >= 8
    assert any(e.start_datetime < now - timedelta(hours=1) for e in events)
    assert any(e.start_datetime > now + timedelta(hours=1) for e in events)


@pytest.mark.django_db
def test_seed_staging_is_idempotent():
    call_command("seed_staging")
    rsvps = EventRSVP.objects.count()
    call_command("seed_staging")
    assert User.objects.filter(phone_number__startswith="+170255501").count() == len(
        PermissionKey.values
    )
    assert User.objects.filter(phone_number__startswith="+170255502").count() == 8
    assert Role.objects.filter(name__startswith="perm: ").count() == len(PermissionKey.values)
    assert Event.objects.filter(title__startswith="[staging] ").count() == len(STAGING_EVENTS)
    assert EventRSVP.objects.count() == rsvps


@pytest.mark.django_db
def test_seed_staging_reset_removes_only_scoped_rows():
    User.objects.create_user(
        phone_number="+17025559999", first_name="real", last_name="person", is_member=True
    )
    call_command("seed_staging")
    call_command("seed_staging", "--reset")
    assert User.objects.filter(phone_number="+17025559999").exists()
    assert User.objects.filter(phone_number__startswith="+170255501").count() == len(
        PermissionKey.values
    )
    assert User.objects.filter(phone_number__startswith="+170255502").count() == 8


@pytest.mark.django_db
def test_seed_staging_refuses_in_production(monkeypatch):
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "production")
    with pytest.raises(Exception):
        call_command("seed_staging")
    assert Role.objects.filter(name__startswith="perm: ").count() == 0


@pytest.mark.django_db
def test_seed_staging_non_member_lifecycle_matches_specs():
    call_command("seed_staging")
    assert User.objects.filter(phone_number__startswith="+170255503").count() == len(
        NON_MEMBER_SPECS
    )
    states = {TOKEN_VALID: 0, TOKEN_EXPIRED: 0, TOKEN_NONE: 0, "with_email": 0, "no_email": 0}
    for index, spec in enumerate(NON_MEMBER_SPECS):
        user = User.objects.get(phone_number=f"+170255503{index:02d}")
        assert user.is_member is False and not user.has_usable_password()
        assert bool(user.email) is spec.has_email
        states["with_email" if spec.has_email else "no_email"] += 1
        states[spec.token_state] += 1
        token = NonMemberRsvpToken.objects.filter(user=user).first()
        if spec.token_state == TOKEN_NONE:
            assert token is None
        elif spec.token_state == TOKEN_EXPIRED:
            assert token is not None and token.is_expired and not token.is_valid
        elif spec.rsvps:
            assert token is not None and token.is_valid
    assert all(v > 0 for v in states.values())
    assert EventRSVP.objects.filter(event__title=NON_MEMBER_EVENT_TITLE).exists()


@pytest.mark.django_db
def test_seed_staging_reset_removes_non_member_band():
    call_command("seed_staging")
    stale_user = User.objects.filter(phone_number__startswith="+170255503").first()
    stale_event = Event.objects.get(title=NON_MEMBER_EVENT_TITLE)
    call_command("seed_staging", "--reset")
    # --reset deletes the band then reseeds it fresh in the same call, mirroring
    # the perm/cond bands (see test_seed_staging_reset_removes_only_scoped_rows).
    assert User.objects.filter(phone_number__startswith="+170255503").count() == len(
        NON_MEMBER_SPECS
    )
    refreshed_user = User.objects.filter(phone_number__startswith="+170255503").first()
    assert refreshed_user.pk != stale_user.pk
    refreshed_event = Event.objects.get(title=NON_MEMBER_EVENT_TITLE)
    assert refreshed_event.pk != stale_event.pk


@pytest.mark.django_db
def test_seed_staging_non_members_idempotent():
    call_command("seed_staging")
    call_command("seed_staging")
    assert User.objects.filter(phone_number__startswith="+170255503").count() == len(
        NON_MEMBER_SPECS
    )


def test_official_events_span_past_today_future_with_capacity_variety():
    official = [e for e in STAGING_EVENTS if e.event_type == EventType.OFFICIAL and e.rsvp_enabled]
    assert len(official) >= 3
    assert any(e.delta_days < 0 for e in official)
    assert any(e.delta_days == 0 for e in official)
    assert any(e.delta_days > 0 for e in official)
    caps = [e.max_attendees for e in official if e.max_attendees is not None]
    assert min(caps) <= 2  # at/over capacity to exercise the waitlist
    assert max(caps) >= 20  # well under capacity


@pytest.mark.django_db
def test_seed_staging_official_events_are_rsvp_enabled():
    call_command("seed_staging")
    for title in (OFFICIAL_PAST_TITLE, OFFICIAL_TODAY_TITLE, OFFICIAL_FULL_TITLE):
        event = Event.objects.get(title=title)
        assert event.event_type == EventType.OFFICIAL
        assert event.rsvp_enabled is True
        assert event.max_attendees is not None


@pytest.mark.django_db
def test_seed_staging_members_cover_all_rsvp_states():
    call_command("seed_staging")
    states = set(
        EventRSVP.objects.filter(user__phone_number__startswith="+170255502").values_list(
            "status", flat=True
        )
    )
    assert {
        RSVPStatus.ATTENDING,
        RSVPStatus.MAYBE,
        RSVPStatus.CANT_GO,
        RSVPStatus.WAITLISTED,
    } <= states


@pytest.mark.django_db
def test_seed_staging_past_official_has_member_and_non_member_attendance_marks():
    call_command("seed_staging")
    marked = EventRSVP.objects.filter(
        event__title=OFFICIAL_PAST_TITLE,
        status=RSVPStatus.ATTENDING,
        attendance__in=[AttendanceStatus.ATTENDED, AttendanceStatus.NO_SHOW],
    )
    assert marked.filter(user__is_member=True).exists()
    assert marked.filter(user__is_member=False).exists()


@pytest.mark.django_db
def test_seed_staging_over_capacity_event_fills_and_waitlists():
    call_command("seed_staging")
    full = Event.objects.get(title=OFFICIAL_FULL_TITLE)
    rsvps = EventRSVP.objects.filter(event=full)
    assert rsvps.filter(status=RSVPStatus.ATTENDING).count() >= full.max_attendees
    assert rsvps.filter(status=RSVPStatus.WAITLISTED).exists()
