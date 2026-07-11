# seed_staging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A dedicated, idempotent `seed_staging` management command that populates the staging deploy with varied events, one single-permission role per `PermissionKey`, a per-permission user for each role (complete profiles), and a separate set of 8 profile-condition users — all onboarding-complete with a known password.

**Architecture:** Follows the existing `seed` command pattern: a `Command(BaseCommand)` orchestrator in `backend/community/management/commands/seed_staging.py` plus static data + pure helpers in a sibling `_seed_staging_data.py`. Roles/users are driven off the `PermissionKey` enum so coverage holds by construction. Idempotent via `get_or_create` + reconcile. A production guard keys off `RAILWAY_ENVIRONMENT_NAME`. Run on demand via a Railway one-off.

**Tech Stack:** Django 5 management command, `django.utils.timezone`, pytest + `call_command`.

## Global Constraints

- Password for all seeded users: `testPassword1@` (passes `AUTH_PASSWORD_VALIDATORS`).
- No top-of-file comments (hook-enforced). No banner/preamble comments. Module docstring is allowed.
- Comments only where the *why* is non-obvious; single-line. Structured docstrings OK.
- Prefer shared types over raw strings: use `PermissionKey`, `EventType`, `Role`.
- Files under 300 LOC target, 500 hard max — split data into `_seed_staging_data.py`.
- Never commit on `main`. This worktree is on branch `chore-seed-staging`. Commit via literal worktree path: `git -C /Users/leahpeker/development/pda/.claude/worktrees/chore-seed-staging commit -F <msgfile>` (single command; no heredoc; add and commit as separate Bash calls).
- No `Co-Authored-By` trailers.
- Reserved phone blocks: per-permission `+170255501NN` (NN=00..11), condition `+170255502NN` (NN=00..07). Disjoint from dev seed `+1702555000x`.
- Role names: `perm: {key}`. Event titles prefixed `[staging] `.
- Verify with `make agent-ci` (from worktree root) before marking complete / opening PR — not per commit.

**Working directory for all commands:** `/Users/leahpeker/development/pda/.claude/worktrees/chore-seed-staging`. Run `make`/`pytest` from there; run `python manage.py` from `backend/`.

---

## File Structure

- Create: `backend/community/management/commands/_seed_staging_data.py` — pure data + helpers: event templates, `PermissionKey`-derived role/user builders, the 8-combination enumerator, the `_is_seed_allowed` guard helper, and `PASSWORD`. No Django model access at import time beyond enum reads.
- Create: `backend/community/management/commands/seed_staging.py` — `Command` orchestrator: guard check, seed roles → per-permission users → condition users → events, print summaries.
- Create: `backend/tests/test_seed_staging.py` — pytest coverage.

---

## Task 1: Pure data module + guard/combination helpers

Build `_seed_staging_data.py` with only pure, importable, unit-testable pieces (no DB). This task's deliverable is the data + helpers with their own tests.

**Files:**
- Create: `backend/community/management/commands/_seed_staging_data.py`
- Test: `backend/tests/test_seed_staging.py`

**Interfaces:**
- Consumes: `users.permissions.PermissionKey`, `community.models.choices.EventType`.
- Produces:
  - `PASSWORD: str = "testPassword1@"`
  - `perm_phone(index: int) -> str` → `f"+170255501{index:02d}"`
  - `cond_phone(index: int) -> str` → `f"+170255502{index:02d}"`
  - `condition_combinations() -> list[tuple[bool, bool, bool]]` → the 8 `(has_email, guidelines_done, sms_done)` tuples in fixed order.
  - `condition_label(combo: tuple[bool, bool, bool]) -> str` → e.g. `"cond: complete"`, `"cond: no-email+needs-sms"`.
  - `cond_email(index: int) -> str` → `f"cond{index:02d}@staging.example"`.
  - `perm_email(key: str) -> str` → `f"perm.{key}@staging.example"`.
  - `is_seed_allowed(env_name: str | None, force: bool) -> bool` → True for `None`/`""`/`"staging"`; for any other value only if `force`.
  - `STAGING_EVENTS: list[SeedStagingEvent]` — dataclass instances (~10) spanning past/current/future.
  - `SeedStagingEvent` dataclass: `title, description, delta_days: int, duration_hours: float, location, event_type: str = EventType.COMMUNITY`.

- [ ] **Step 1: Write failing tests for the pure helpers**

Create `backend/tests/test_seed_staging.py`:

```python
import pytest

from community.management.commands._seed_staging_data import (
    PASSWORD,
    STAGING_EVENTS,
    condition_combinations,
    condition_label,
    cond_email,
    cond_phone,
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_seed_staging.py -q`
Expected: FAIL — `ModuleNotFoundError`/`ImportError` (module doesn't exist yet).

- [ ] **Step 3: Implement `_seed_staging_data.py`**

Create `backend/community/management/commands/_seed_staging_data.py`:

```python
"""Static data + pure helpers for the `seed_staging` command."""

from dataclasses import dataclass

from community.models.choices import EventType

PASSWORD = "testPassword1@"


@dataclass
class SeedStagingEvent:
    title: str
    description: str
    delta_days: int
    duration_hours: float
    location: str
    event_type: str = EventType.COMMUNITY


def perm_phone(index: int) -> str:
    return f"+170255501{index:02d}"


def cond_phone(index: int) -> str:
    return f"+170255502{index:02d}"


def perm_email(key: str) -> str:
    return f"perm.{key}@staging.example"


def cond_email(index: int) -> str:
    return f"cond{index:02d}@staging.example"


def condition_combinations() -> list[tuple[bool, bool, bool]]:
    """All 8 (has_email, guidelines_done, sms_done) patterns, fixed order."""
    return [
        (has_email, guidelines_done, sms_done)
        for has_email in (True, False)
        for guidelines_done in (True, False)
        for sms_done in (True, False)
    ]


def condition_label(combo: tuple[bool, bool, bool]) -> str:
    has_email, guidelines_done, sms_done = combo
    parts: list[str] = []
    if not has_email:
        parts.append("no-email")
    if not guidelines_done:
        parts.append("needs-guidelines")
    if not sms_done:
        parts.append("needs-sms")
    return "cond: " + ("complete" if not parts else "+".join(parts))


def is_seed_allowed(env_name: str | None, force: bool) -> bool:
    """Allow local/unset and staging; refuse any other env unless forced."""
    if not env_name or env_name == "staging":
        return True
    return force


STAGING_EVENTS = [
    SeedStagingEvent(
        title="[staging] past potluck",
        description="a wrapped-up community potluck from last month.",
        delta_days=-30,
        duration_hours=3,
        location="community center",
    ),
    SeedStagingEvent(
        title="[staging] last week's film night",
        description="documentary screening and discussion.",
        delta_days=-7,
        duration_hours=2,
        location="the annex",
    ),
    SeedStagingEvent(
        title="[staging] yesterday's kitchen social",
        description="casual cook-and-hang.",
        delta_days=-1,
        duration_hours=2.5,
        location="shared kitchen",
    ),
    SeedStagingEvent(
        title="[staging] happening today",
        description="drop-in tabling and outreach.",
        delta_days=0,
        duration_hours=4,
        location="market square",
        event_type=EventType.OFFICIAL,
    ),
    SeedStagingEvent(
        title="[staging] tomorrow's cooking workshop",
        description="plant-based basics, hands-on.",
        delta_days=1,
        duration_hours=2,
        location="teaching kitchen",
    ),
    SeedStagingEvent(
        title="[staging] weekend park cleanup",
        description="gloves and bags provided.",
        delta_days=3,
        duration_hours=3,
        location="riverside park",
    ),
    SeedStagingEvent(
        title="[staging] next week's book club",
        description="this month's read: collective liberation.",
        delta_days=7,
        duration_hours=1.5,
        location="library room b",
    ),
    SeedStagingEvent(
        title="[staging] monthly official meeting",
        description="agenda, updates, and open floor.",
        delta_days=14,
        duration_hours=2,
        location="main hall",
        event_type=EventType.OFFICIAL,
    ),
    SeedStagingEvent(
        title="[staging] future festival",
        description="all-day tabling, food, and music.",
        delta_days=45,
        duration_hours=8,
        location="fairgrounds",
    ),
    SeedStagingEvent(
        title="[staging] far-future retreat",
        description="weekend planning retreat.",
        delta_days=90,
        duration_hours=48,
        location="the lodge",
    ),
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_seed_staging.py -q`
Expected: PASS (all pure-helper tests).

- [ ] **Step 5: Typecheck + lint the new file**

Run: `make agent-typecheck && make agent-lint`
Expected: no errors. Fix any before committing.

- [ ] **Step 6: Commit**

```bash
git -C /Users/leahpeker/development/pda/.claude/worktrees/chore-seed-staging add backend/community/management/commands/_seed_staging_data.py backend/tests/test_seed_staging.py
git -C /Users/leahpeker/development/pda/.claude/worktrees/chore-seed-staging commit -F <msgfile>
```
Message: `feat(seed): staging seed data module + pure helpers (Issue 653)`

---

## Task 2: `seed_staging` command — roles + per-permission users

Build the command orchestrator, seeding roles and per-permission users. Events + condition users come in Task 3; this task delivers a runnable command with the first two data sets.

**Files:**
- Create: `backend/community/management/commands/seed_staging.py`
- Test: `backend/tests/test_seed_staging.py`

**Interfaces:**
- Consumes (Task 1): `PASSWORD`, `perm_phone`, `perm_email`, `is_seed_allowed`, `STAGING_EVENTS` (used in Task 3).
- Consumes (codebase): `users.permissions.PermissionKey`, `users.roles.Role`, `users.models.User`, `django.utils.timezone`, `django.core.management.base.BaseCommand`, `django.core.management.base.CommandError`.
- Produces: management command `seed_staging` with `--reset` and `--force` flags. Helper methods `_seed_perm_roles() -> dict[str, Role]`, `_seed_perm_users(roles) -> list[User]`.

- [ ] **Step 1: Write failing tests for roles + per-permission users**

Append to `backend/tests/test_seed_staging.py`:

```python
from django.core.management import call_command
from django.contrib.auth.hashers import check_password

from users.models import User
from users.permissions import PermissionKey
from users.roles import Role


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_seed_staging.py -k "one_role_per_permission or perm_users_hold" -q`
Expected: FAIL — `CommandError: Unknown command: 'seed_staging'`.

- [ ] **Step 3: Implement the command (roles + per-permission users)**

Create `backend/community/management/commands/seed_staging.py`:

```python
"""Seed the staging deploy with events, single-permission roles, and matching users."""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from users.permissions import PermissionKey
from users.roles import Role

from ._seed_staging_data import (
    PASSWORD,
    is_seed_allowed,
    perm_email,
    perm_phone,
)

User = get_user_model()


class Command(BaseCommand):
    help = "Seed staging with events, single-permission roles, and matching users."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete staging-scoped rows first.")
        parser.add_argument("--force", action="store_true", help="Run even if the environment is not staging.")

    def handle(self, *args, **options):
        env_name = os.environ.get("RAILWAY_ENVIRONMENT_NAME")
        self.stdout.write(f"detected environment: {env_name or 'local/unset'}")
        if not is_seed_allowed(env_name, force=options["force"]):
            raise CommandError(
                f"refusing to seed in environment '{env_name}'. pass --force to override."
            )

        with transaction.atomic():
            if options["reset"]:
                self._reset()
            roles = self._seed_perm_roles()
            self._seed_perm_users(roles)

    def _reset(self) -> None:
        pass  # implemented in Task 3

    def _seed_perm_roles(self) -> dict[str, Role]:
        roles: dict[str, Role] = {}
        for key in PermissionKey.values:
            role, created = Role.objects.get_or_create(
                name=f"perm: {key}",
                defaults={"permissions": [key], "is_default": False},
            )
            if not created and role.permissions != [key]:
                role.permissions = [key]
                role.save(update_fields=["permissions"])
            roles[key] = role
            self.stdout.write(f"  {'created' if created else 'exists'} role: {role.name}")
        return roles

    def _seed_perm_users(self, roles: dict[str, Role]) -> list[User]:
        users: list[User] = []
        now = timezone.now()
        for index, key in enumerate(PermissionKey.values):
            user, created = User.objects.get_or_create(
                phone_number=perm_phone(index),
                defaults={
                    "display_name": f"perm: {key}",
                    "email": perm_email(key),
                    "is_member": True,
                    "needs_onboarding": False,
                    "onboarded_at": now,
                    "guidelines_consent_at": now,
                    "sms_consent_at": now,
                },
            )
            if created:
                user.set_password(PASSWORD)
                user.save(update_fields=["password"])
            user.roles.set([roles[key]])
            users.append(user)
            self.stdout.write(f"  {'created' if created else 'exists'} user: {user.display_name}")
        return users
```

Note: `user.roles.set([...])` reconciles the role set to exactly that role on every run; the `reject_role_for_non_member` signal is satisfied because `is_member=True`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_seed_staging.py -k "one_role_per_permission or perm_users_hold" -q`
Expected: PASS.

- [ ] **Step 5: Typecheck + lint**

Run: `make agent-typecheck && make agent-lint`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git -C /Users/leahpeker/development/pda/.claude/worktrees/chore-seed-staging add backend/community/management/commands/seed_staging.py backend/tests/test_seed_staging.py
git -C /Users/leahpeker/development/pda/.claude/worktrees/chore-seed-staging commit -F <msgfile>
```
Message: `feat(seed): seed_staging command with roles + per-permission users (Issue 653)`

---

## Task 3: Condition users, events, reset, summary

Complete the command: the separate 8-user condition set, events, `--reset` scoping, and summary output.

**Files:**
- Modify: `backend/community/management/commands/seed_staging.py`
- Test: `backend/tests/test_seed_staging.py`

**Interfaces:**
- Consumes (Task 1): `STAGING_EVENTS`, `condition_combinations`, `condition_label`, `cond_phone`, `cond_email`.
- Consumes (codebase): `community.models.Event`, `datetime.timedelta`.
- Produces: methods `_seed_condition_users() -> list[User]`, `_seed_events(created_by) -> list[Event]`, a filled `_reset()`, and `_print_summary(...)`. The built-in `member` role is fetched/created like `seed.py` does.

- [ ] **Step 1: Write failing tests for condition users, events, reset**

Append to `backend/tests/test_seed_staging.py`:

```python
from datetime import timedelta

from community.models import Event
from community.management.commands._seed_staging_data import (
    condition_combinations,
    cond_phone,
)


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
    perm = set(User.objects.filter(phone_number__startswith="+170255501").values_list("phone_number", flat=True))
    cond = set(User.objects.filter(phone_number__startswith="+170255502").values_list("phone_number", flat=True))
    assert len(perm) == 12
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
    call_command("seed_staging")
    assert User.objects.filter(phone_number__startswith="+170255501").count() == 12
    assert User.objects.filter(phone_number__startswith="+170255502").count() == 8
    assert Role.objects.filter(name__startswith="perm: ").count() == len(PermissionKey.values)
    assert Event.objects.filter(title__startswith="[staging] ").count() == len(STAGING_EVENTS)


@pytest.mark.django_db
def test_seed_staging_reset_removes_only_scoped_rows():
    other = User.objects.create_user(phone_number="+17025559999", display_name="real person", is_member=True)
    call_command("seed_staging")
    call_command("seed_staging", "--reset")
    assert User.objects.filter(phone_number="+17025559999").exists()
    assert User.objects.filter(phone_number__startswith="+170255501").count() == 12
    assert User.objects.filter(phone_number__startswith="+170255502").count() == 8


@pytest.mark.django_db
def test_seed_staging_refuses_in_production(monkeypatch):
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "production")
    with pytest.raises(Exception):
        call_command("seed_staging")
    assert Role.objects.filter(name__startswith="perm: ").count() == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_seed_staging.py -k "condition_users or disjoint or events_span or idempotent or reset_removes or refuses" -q`
Expected: FAIL — condition users / events don't exist yet; `--reset` is a no-op; refuse-in-prod already passes but others fail.

- [ ] **Step 3: Implement condition users, events, reset, summary**

Edit `backend/community/management/commands/seed_staging.py`.

Add imports at top (after existing imports):

```python
from datetime import timedelta

from community.models import Event

from ._seed_staging_data import (
    STAGING_EVENTS,
    cond_email,
    cond_phone,
    condition_combinations,
    condition_label,
)
```

Replace `handle` body's atomic block to seed all sets and print a summary:

```python
        with transaction.atomic():
            if options["reset"]:
                self._reset()
            roles = self._seed_perm_roles()
            perm_users = self._seed_perm_users(roles)
            cond_users = self._seed_condition_users()
            admin = perm_users[0] if perm_users else None
            events = self._seed_events(admin)
        self._print_summary(roles, perm_users, cond_users, events)
```

Replace the placeholder `_reset` with real scoping:

```python
    def _reset(self) -> None:
        Event.objects.filter(title__startswith="[staging] ").delete()
        User.objects.filter(phone_number__startswith="+170255501").delete()
        User.objects.filter(phone_number__startswith="+170255502").delete()
        Role.objects.filter(name__startswith="perm: ").delete()
        self.stdout.write("  reset: removed staging-scoped rows")
```

Add the member-role fetch, condition users, events, and summary:

```python
    def _member_role(self) -> Role:
        role, _ = Role.objects.get_or_create(name="member", defaults={"is_default": True})
        return role

    def _seed_condition_users(self) -> list[User]:
        member_role = self._member_role()
        now = timezone.now()
        users: list[User] = []
        for index, combo in enumerate(condition_combinations()):
            has_email, guidelines_done, sms_done = combo
            user, created = User.objects.get_or_create(
                phone_number=cond_phone(index),
                defaults={"display_name": condition_label(combo), "is_member": True},
            )
            user.email = cond_email(index) if has_email else None
            user.guidelines_consent_at = now if guidelines_done else None
            user.sms_consent_at = now if sms_done else None
            user.needs_onboarding = False
            user.onboarded_at = now
            user.display_name = condition_label(combo)
            user.save(update_fields=[
                "email", "guidelines_consent_at", "sms_consent_at",
                "needs_onboarding", "onboarded_at", "display_name",
            ])
            if created:
                user.set_password(PASSWORD)
                user.save(update_fields=["password"])
            user.roles.set([member_role])
            users.append(user)
            self.stdout.write(f"  {'created' if created else 'exists'} user: {user.display_name}")
        return users

    def _seed_events(self, created_by) -> list[Event]:
        now = timezone.now()
        events: list[Event] = []
        for data in STAGING_EVENTS:
            start = now + timedelta(days=data.delta_days)
            end = start + timedelta(hours=data.duration_hours)
            event, created = Event.objects.get_or_create(
                title=data.title,
                defaults={
                    "description": data.description,
                    "start_datetime": start,
                    "end_datetime": end,
                    "location": data.location,
                    "event_type": data.event_type,
                    "created_by": created_by,
                },
            )
            events.append(event)
            self.stdout.write(f"  {'created' if created else 'exists'} event: {data.title}")
        return events

    def _print_summary(self, roles, perm_users, cond_users, events) -> None:
        self.stdout.write("")
        self.stdout.write(f"password for all seeded users: {PASSWORD}")
        self.stdout.write(f"events: {len(events)}  roles: {len(roles)}  "
                          f"perm users: {len(perm_users)}  condition users: {len(cond_users)}")
        self.stdout.write("per-permission users (phone -> role):")
        for user in perm_users:
            names = ", ".join(user.roles.values_list("name", flat=True))
            self.stdout.write(f"  {user.phone_number} -> {names}")
        self.stdout.write("profile-condition users (phone -> pattern):")
        for user in cond_users:
            self.stdout.write(f"  {user.phone_number} -> {user.display_name}")
```

Note: condition users reconcile their profile fields on every run (set outside the `created` branch) so the intended pattern is stable even if the row pre-existed.

- [ ] **Step 4: Run the full test file**

Run: `cd backend && uv run pytest tests/test_seed_staging.py -q`
Expected: PASS (all tests).

- [ ] **Step 5: Run the command locally to eyeball output**

Run: `cd backend && DJANGO_SETTINGS_MODULE=config.settings uv run python manage.py seed_staging 2>&1 | tail -40`
Expected: two summary tables, sensible counts, no traceback. (Uses the worktree's SQLite/dev DB — safe.)

- [ ] **Step 6: Commit**

```bash
git -C /Users/leahpeker/development/pda/.claude/worktrees/chore-seed-staging add backend/community/management/commands/seed_staging.py backend/tests/test_seed_staging.py
git -C /Users/leahpeker/development/pda/.claude/worktrees/chore-seed-staging commit -F <msgfile>
```
Message: `feat(seed): condition users, events, --reset, and summary for seed_staging (Issue 653)`

---

## Task 4: Documentation + pre-PR CI gate

Document how to run it and verify the whole suite.

**Files:**
- Modify: `CLAUDE.md` (add `seed_staging` to the dev-commands list) — one line.
- Modify: `docs/superpowers/specs/2026-07-09-seed-staging-design.md` — none needed; already current.

- [ ] **Step 1: Add a Makefile-adjacent note to CLAUDE.md**

In `CLAUDE.md`, under the development-commands code block or Standards, add a single line documenting the on-demand staging run:

```
# Staging demo data (run on demand against staging, never prod):
#   railway run --environment staging python backend/manage.py seed_staging
```

Place it as a comment line inside the existing ```bash dev-commands block, after `make seed`.

- [ ] **Step 2: Run the full pre-PR CI gate**

Run: `make agent-ci`
Expected: all green (ruff, ty, complexity, pytest, frontend checks unaffected). Fix anything that fails, re-run until clean.

- [ ] **Step 3: Commit**

```bash
git -C /Users/leahpeker/development/pda/.claude/worktrees/chore-seed-staging add CLAUDE.md
git -C /Users/leahpeker/development/pda/.claude/worktrees/chore-seed-staging commit -F <msgfile>
```
Message: `docs(seed): document on-demand staging seed run (Issue 653)`

- [ ] **Step 4: Open the PR (draft)**

Use the `/open-pr` skill (or `gh pr create --draft`) targeting `main`, linking Issue 653. Do not merge.

---

## Notes for the implementer

- The `reject_role_for_non_member` m2m signal raises `ValueError` if a role is assigned to a non-member. All seeded users are `is_member=True`, so `user.roles.set([...])` is safe.
- `User.email` has a partial unique constraint (`unique_non_blank_email`) — every seeded email is distinct by construction (`perm.{key}@...`, `cond{index:02d}@...`).
- `Event` defaults: `status=EventStatus.ACTIVE`, `visibility=PageVisibility.PUBLIC`, so seeded events appear on the public calendar without extra fields.
- `Role.name` is `max_length=50`; longest role name `perm: approve_join_requests` (27 chars) fits.
- Do not add top-of-file comments (hook-enforced). Module docstrings are fine.
