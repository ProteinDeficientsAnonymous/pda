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
