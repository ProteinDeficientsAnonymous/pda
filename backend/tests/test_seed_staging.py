import pytest
from community.management.commands._seed_staging_data import (
    PASSWORD,
    STAGING_EVENTS,
    cond_email,
    cond_phone,
    condition_combinations,
    condition_label,
    is_seed_allowed,
    perm_email,
    perm_phone,
)
from django.contrib.auth.hashers import check_password
from django.core.management import call_command
from users.models import User
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
    perm = {perm_phone(i) for i in range(12)}
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
