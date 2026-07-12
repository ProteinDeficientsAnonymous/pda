# PR1a — Backend Name Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `first_name` / `last_name` to `User` and `JoinRequest`, backfill from `display_name` via the parse rule, and expose both old and new name fields in the API — without breaking the existing frontend.

**Architecture:** Backend-first transition. New `first_name` (required) + `last_name` (optional) columns are added and backfilled; the legacy `display_name` column is **kept and auto-synced** (`display_name = full_name`) on every save, so the current frontend keeps working. The API sends both shapes. `display_name` is dropped later in PR1c.

**Tech Stack:** Django 5, Django Ninja, Pydantic, pytest. Per-worktree SQLite (`make run-sqlite` / `make agent-test`).

## Global Constraints

- Backend uses Django Ninja with tuple returns `(status_code, data)`; errors as `{"detail": "..."}`; success as `{"message": "..."}`.
- Text fields default to `""`, never `null`. `blank=True` for optional text.
- Prefer shared types/constants over raw strings (`.claude/rules/prefer-types-over-strings.md`).
- Field-length limits live in `backend/community/_field_limits.py` (`FieldLimit`), mirrored in the frontend later.
- No top-of-file banner comments (hook-enforced). Comment only non-obvious *why*.
- Keep files under 300 lines where practical, 500 hard max.
- Run `make agent-typecheck` + relevant `make agent-test` while iterating; `make agent-ci` once before the PR.
- Commit from the worktree with a message file: `git -C /Users/leahpeker/development/pda/.claude/worktrees/feat-split-name-first-last commit -F <scratchpad>/msg.txt` (single git invocation per Bash call; literal absolute path).
- Do NOT drop `display_name` in this PR — that is PR1c.

## Parse rule (used by the data migration)

Given a `display_name` string:
- Split on whitespace into words (`display_name.split()`).
- 0 words → `first_name = ""`, `last_name = ""`.
- 1 word → `first_name = word`, `last_name = ""`.
- 2+ words → `last_name = words[-1]`, `first_name = " ".join(words[:-1])`.

This lives as a module-level helper `parse_display_name(display_name: str) -> tuple[str, str]` so it's importable and unit-testable independent of the migration.

---

## File Structure

- `backend/users/_name_parsing.py` — **create**. `parse_display_name()` helper.
- `backend/users/models.py` — **modify**. Add `first_name`/`last_name` fields; `full_name` property; `save()` sync; `REQUIRED_FIELDS`.
- `backend/users/migrations/0032_user_first_last_name.py` — **create**. Schema migration (nullable add).
- `backend/users/migrations/0033_backfill_user_names.py` — **create**. Data migration.
- `backend/users/migrations/0034_user_first_name_notnull.py` — **create**. first_name non-null.
- `backend/community/models/join_form.py` — **modify**. Same fields on `JoinRequest`.
- `backend/community/migrations/00XX_joinrequest_first_last_name.py` + backfill + notnull — **create** (3 migrations; numbers resolved by `makemigrations`).
- `backend/community/_field_limits.py` — **modify**. Add `FIRST_NAME`, `LAST_NAME`.
- `backend/users/schemas.py` — **modify**. Add first/last/full_name to outputs; accept first/last on inputs.
- `backend/users/_helpers.py` — **modify**. `_create_user_with_role` takes first/last.
- `backend/community/_join_request_approval.py` — **modify**. Copy first/last to User.
- `backend/community/_join_request_submit.py`, `_join_request_resend.py` — **modify**. Carry first/last.
- `backend/tests/conftest.py` — **modify**. Fixtures set first/last.
- `backend/tests/test_name_parsing.py` — **create**. Parse-rule unit tests.
- `backend/tests/test_name_split_api.py` — **create**. Schema round-trip + save-sync tests.

---

## Task 1: Parse-rule helper

**Files:**
- Create: `backend/users/_name_parsing.py`
- Test: `backend/tests/test_name_parsing.py`

**Interfaces:**
- Produces: `parse_display_name(display_name: str) -> tuple[str, str]` returning `(first_name, last_name)`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_name_parsing.py
import pytest

from users._name_parsing import parse_display_name


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("", ("", "")),
        ("   ", ("", "")),
        ("Cher", ("Cher", "")),
        ("Ada Lovelace", ("Ada", "Lovelace")),
        ("Mary Jane Watson", ("Mary Jane", "Watson")),
        ("  extra   spaces  here ", ("extra spaces", "here")),
    ],
)
def test_parse_display_name(raw, expected):
    assert parse_display_name(raw) == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_name_parsing.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'users._name_parsing'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/users/_name_parsing.py
def parse_display_name(display_name: str) -> tuple[str, str]:
    """Split a legacy display_name into (first_name, last_name).

    Last whitespace-delimited word becomes the last name; everything before it
    is the first name. A single word is the first name with a blank last name.
    """
    words = (display_name or "").split()
    if not words:
        return "", ""
    if len(words) == 1:
        return words[0], ""
    return " ".join(words[:-1]), words[-1]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_name_parsing.py -v`
Expected: PASS (6 cases)

- [ ] **Step 5: Commit**

```bash
printf 'feat(users): add display_name parse helper (Issue 532)\n' > <SCRATCH>/msg.txt
git -C <WORKTREE> add backend/users/_name_parsing.py backend/tests/test_name_parsing.py
git -C <WORKTREE> commit -F <SCRATCH>/msg.txt
```

---

## Task 2: User model fields + full_name + save sync

**Files:**
- Modify: `backend/users/models.py` (User class, lines ~75–130)
- Test: `backend/tests/test_name_split_api.py`

**Interfaces:**
- Consumes: `parse_display_name` (not used here — the model just stores).
- Produces: `User.first_name: str`, `User.last_name: str`, `User.full_name` (property), `User.save()` syncs `display_name = full_name`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_name_split_api.py
import pytest

from users.models import User


@pytest.mark.django_db
class TestUserFullName:
    def test_full_name_combines_first_last(self):
        u = User.objects.create_user(
            phone_number="+15551230001", first_name="Ada", last_name="Lovelace"
        )
        assert u.full_name == "Ada Lovelace"

    def test_full_name_first_only(self):
        u = User.objects.create_user(phone_number="+15551230002", first_name="Cher")
        assert u.full_name == "Cher"

    def test_save_syncs_display_name(self):
        u = User.objects.create_user(
            phone_number="+15551230003", first_name="Ada", last_name="Lovelace"
        )
        u.refresh_from_db()
        assert u.display_name == "Ada Lovelace"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_name_split_api.py -v`
Expected: FAIL — `TypeError` / unexpected keyword `first_name` (field not yet defined).

- [ ] **Step 3: Modify the model**

In `backend/users/models.py`, inside `class User(AbstractUser)`, replace the `display_name` field line and the removed-inherited-fields block:

```python
    display_name = models.CharField(max_length=64, blank=True)
    first_name = models.CharField(max_length=64, blank=True, default="")
    last_name = models.CharField(max_length=64, blank=True, default="")
```

(Keep `display_name` — it is the transitional column. `first_name`/`last_name` are added as
blank+default here so the pre-backfill migration state is valid; requiredness is enforced at
the schema layer, and non-null is set in migration 0034.)

Remove the `first_name = None` / `last_name = None` lines from the "Remove inherited
AbstractUser fields" block (keep `username = None`):

```python
    # Remove inherited AbstractUser fields
    username = None
```

Update `REQUIRED_FIELDS`:

```python
    REQUIRED_FIELDS = ["first_name"]
```

Add the `full_name` property and `save()` sync (place `full_name` near `__str__`):

```python
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def save(self, *args, **kwargs):
        # Keep the transitional display_name column in sync until PR1c drops it.
        self.display_name = self.full_name
        super().save(*args, **kwargs)

    def __str__(self):
        return self.full_name or self.phone_number
```

Note: `AbstractUser` defines `get_full_name()`; we add a `full_name` **property**, which does not collide. Do not override `get_full_name`.

- [ ] **Step 4: Create + run the schema migration**

Run: `cd backend && uv run python manage.py makemigrations users`
Expected: creates `0032_...` adding `first_name`, `last_name` (nullable/blank) and altering `display_name` is unnecessary. Rename the file to `0032_user_first_last_name.py` if the generated name differs, and verify it only adds the two fields.

Run: `cd backend && uv run python manage.py migrate users`
Expected: applies cleanly.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_name_split_api.py -v`
Expected: PASS (3 cases)

- [ ] **Step 6: Commit**

```bash
printf 'feat(users): add first/last name fields with full_name + display_name sync (Issue 532)\n' > <SCRATCH>/msg.txt
git -C <WORKTREE> add backend/users/models.py backend/users/migrations/0032_user_first_last_name.py backend/tests/test_name_split_api.py
git -C <WORKTREE> commit -F <SCRATCH>/msg.txt
```

---

## Task 3: User backfill data migration + non-null

**Files:**
- Create: `backend/users/migrations/0033_backfill_user_names.py`
- Create: `backend/users/migrations/0034_user_first_name_notnull.py`
- Test: `backend/tests/test_name_split_api.py` (add a migration-behavior test using existing rows)

**Interfaces:**
- Consumes: `parse_display_name`.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_name_split_api.py`:

```python
@pytest.mark.django_db
class TestBackfillParsing:
    """The backfill logic (parse_display_name) applied to representative names."""

    def test_backfill_maps_existing_names(self):
        from users._name_parsing import parse_display_name

        u = User.objects.create_user(phone_number="+15551230100", first_name="x")
        # Simulate a legacy row: display_name set, names to be derived.
        u.first_name, u.last_name = parse_display_name("Grace Hopper")
        u.save()
        u.refresh_from_db()
        assert (u.first_name, u.last_name) == ("Grace", "Hopper")
        assert u.display_name == "Grace Hopper"
```

- [ ] **Step 2: Run test to verify it passes already (logic reused)**

Run: `cd backend && uv run pytest tests/test_name_split_api.py::TestBackfillParsing -v`
Expected: PASS — this guards that parse + save-sync produce the intended row shape. (The migration itself is exercised by the full suite migrating a fresh DB.)

- [ ] **Step 3: Write the data migration**

```python
# backend/users/migrations/0033_backfill_user_names.py
from django.db import migrations

from users._name_parsing import parse_display_name


def backfill(apps, schema_editor):
    User = apps.get_model("users", "User")
    for user in User.objects.all().iterator():
        first, last = parse_display_name(user.display_name or "")
        user.first_name = first
        user.last_name = last
        user.save(update_fields=["first_name", "last_name"])


def noop_reverse(apps, schema_editor):
    # display_name is untouched, so reversing just leaves the parsed columns.
    pass


class Migration(migrations.Migration):
    dependencies = [("users", "0032_user_first_last_name")]
    operations = [migrations.RunPython(backfill, noop_reverse)]
```

Note: the migration imports the app-level `parse_display_name` (safe — it's a pure function
with no model imports at module load that would break historical-model isolation). If the
project forbids importing app code into migrations, inline the parse logic into `backfill`
instead.

- [ ] **Step 4: Write the non-null migration**

Run: after editing the model in Task 2, `first_name`/`last_name` are `blank=True, default=""`. To make `first_name` non-null at the DB level (it already is, since `default=""` and no `null=True`), no ALTER is needed — SQLite/Postgres columns are `NOT NULL DEFAULT ''`. **Therefore migration 0034 is only needed if the model changes `first_name` to remove `default`/`blank`.** For PR1a we keep `blank=True, default=""` (requiredness enforced in schemas), so **skip 0034** — delete it from the file list.

Confirm no pending migration:

Run: `cd backend && uv run python manage.py makemigrations users --check --dry-run`
Expected: "No changes detected".

- [ ] **Step 5: Run the migration on a fresh DB**

Run: `make dev-db-reset` then `cd backend && uv run pytest tests/test_name_split_api.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
printf 'feat(users): backfill first/last name from display_name (Issue 532)\n' > <SCRATCH>/msg.txt
git -C <WORKTREE> add backend/users/migrations/0033_backfill_user_names.py backend/tests/test_name_split_api.py
git -C <WORKTREE> commit -F <SCRATCH>/msg.txt
```

---

## Task 4: JoinRequest fields + backfill

**Files:**
- Modify: `backend/community/models/join_form.py` (JoinRequest, line ~33)
- Create: community migrations (schema add + backfill) — numbers via `makemigrations`.
- Test: `backend/tests/test_name_split_api.py`

**Interfaces:**
- Produces: `JoinRequest.first_name`, `JoinRequest.last_name`, `JoinRequest.full_name` property.

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.django_db
class TestJoinRequestNames:
    def test_join_request_full_name(self):
        from community.models.join_form import JoinRequest

        jr = JoinRequest.objects.create(
            first_name="Ada", last_name="Lovelace", phone_number="+15551239999"
        )
        assert jr.full_name == "Ada Lovelace"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_name_split_api.py::TestJoinRequestNames -v`
Expected: FAIL — unexpected keyword `first_name`.

- [ ] **Step 3: Modify the model**

In `backend/community/models/join_form.py`, in `class JoinRequest`, keep `display_name` and add:

```python
    display_name = models.CharField(max_length=64)
    first_name = models.CharField(max_length=64, blank=True, default="")
    last_name = models.CharField(max_length=64, blank=True, default="")
```

Add a `full_name` property and sync `display_name` on save (mirror the User approach):

```python
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def save(self, *args, **kwargs):
        if self.full_name:
            self.display_name = self.full_name
        super().save(*args, **kwargs)
```

(Guard on `self.full_name` truthiness so a legacy row created with only `display_name`
doesn't get blanked — the public submit path in Task 6 always sets first/last.)

- [ ] **Step 4: Make + apply migrations**

Run: `cd backend && uv run python manage.py makemigrations community`
Expected: schema migration adding the two fields.

Then create a backfill migration by hand mirroring Task 3 (`apps.get_model("community", "JoinRequest")`, same `parse_display_name`). Name it `..._backfill_joinrequest_names.py`.

Run: `cd backend && uv run python manage.py migrate community`
Expected: applies cleanly.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_name_split_api.py::TestJoinRequestNames -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
printf 'feat(community): add first/last name to JoinRequest with backfill (Issue 532)\n' > <SCRATCH>/msg.txt
git -C <WORKTREE> add backend/community/models/join_form.py backend/community/migrations/*.py backend/tests/test_name_split_api.py
git -C <WORKTREE> commit -F <SCRATCH>/msg.txt
```

---

## Task 5: Field limits + schemas (outputs add fields, inputs accept first/last)

**Files:**
- Modify: `backend/community/_field_limits.py`
- Modify: `backend/users/schemas.py`
- Test: `backend/tests/test_name_split_api.py`

**Interfaces:**
- Consumes: `User.first_name/last_name/full_name`.
- Produces: `UserOut`/`MemberProfileOut`/`MemberDirectoryOut`/`UserSearchOut`/`UserCreateOut` carry `first_name`, `last_name`, `full_name`, and still `display_name`. `UserCreateIn`/`UserPatchIn`/`MePatchIn`/`OnboardingIn` accept `first_name`, `last_name`.

- [ ] **Step 1: Add field limits**

In `backend/community/_field_limits.py`, under `DISPLAY_NAME = 64`:

```python
    DISPLAY_NAME = 64
    FIRST_NAME = 64
    LAST_NAME = 64
```

- [ ] **Step 2: Write the failing test**

```python
@pytest.mark.django_db
class TestUserOutSchema:
    def test_user_out_includes_new_and_legacy_names(self):
        from users.schemas import UserOut

        u = User.objects.create_user(
            phone_number="+15551230200", first_name="Ada", last_name="Lovelace"
        )
        out = UserOut.from_user(u)
        assert out.first_name == "Ada"
        assert out.last_name == "Lovelace"
        assert out.full_name == "Ada Lovelace"
        assert out.display_name == "Ada Lovelace"  # transitional
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_name_split_api.py::TestUserOutSchema -v`
Expected: FAIL — `UserOut` has no `first_name`.

- [ ] **Step 4: Update output schemas**

In `backend/users/schemas.py`, add fields to `UserOut` (keep `display_name`):

```python
class UserOut(BaseModel):
    id: str
    phone_number: str
    display_name: str
    first_name: str = ""
    last_name: str = ""
    full_name: str = ""
    email: str = ""
    ...
```

In `UserOut.from_user`, add:

```python
            display_name=user.display_name,
            first_name=user.first_name,
            last_name=user.last_name,
            full_name=user.full_name,
```

Add `first_name`, `last_name`, `full_name` (with `= ""` defaults) to `MemberProfileOut`,
`MemberDirectoryOut`, `UserSearchOut`, and `UserCreateOut`. For the schemas built by
`.from_*`/manual construction, populate them from the model at each construction site (grep
for `MemberProfileOut(`, `MemberDirectoryOut(`, `UserSearchOut(`, `UserCreateOut(` and add
the three kwargs). Keep `display_name` populated too.

- [ ] **Step 5: Update input schemas**

Add optional first/last to input schemas, keeping `display_name` optional:

```python
class UserCreateIn(BaseModel):
    phone_number: str = Field(max_length=FieldLimit.PHONE)
    display_name: str = Field(default="", max_length=FieldLimit.DISPLAY_NAME)
    first_name: str = Field(default="", max_length=FieldLimit.FIRST_NAME)
    last_name: str = Field(default="", max_length=FieldLimit.LAST_NAME)
    email: OptionalEmail = None
    role_id: str | None = None
```

Same pattern (add `first_name`/`last_name`, keep `display_name`) for `UserPatchIn`,
`MePatchIn`, `OnboardingIn`.

- [ ] **Step 6: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_name_split_api.py::TestUserOutSchema -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
printf 'feat(users): expose first/last/full_name in schemas alongside display_name (Issue 532)\n' > <SCRATCH>/msg.txt
git -C <WORKTREE> add backend/community/_field_limits.py backend/users/schemas.py backend/tests/test_name_split_api.py
git -C <WORKTREE> commit -F <SCRATCH>/msg.txt
```

---

## Task 6: Wire write paths (create / patch / onboarding / join submit + approval)

**Files:**
- Modify: `backend/users/_helpers.py` (`_create_user_with_role`)
- Modify: `backend/users/_management.py`, `backend/users/_auth.py` (call sites + patch/onboarding endpoints)
- Modify: `backend/community/_join_request_submit.py`, `_join_request_resend.py`, `_join_request_approval.py`
- Test: `backend/tests/test_name_split_api.py`

**Interfaces:**
- Consumes: input schemas from Task 5.
- Produces: `_create_user_with_role(phone, first_name, last_name, email, role_id, *, requesting_user, consent=None)`.

- [ ] **Step 1: Write the failing test (approval copies first/last)**

```python
@pytest.mark.django_db
class TestApprovalCopiesNames:
    def test_new_user_gets_first_last_from_join_request(self, manage_users_user):
        from community.models.join_form import JoinRequest
        from community._join_request_approval import _provision_approved_user

        jr = JoinRequest.objects.create(
            first_name="Grace", last_name="Hopper", phone_number="+15551231212"
        )
        token, created = _provision_approved_user(jr, manage_users_user)
        assert created is True
        u = User.objects.get(phone_number="+15551231212")
        assert (u.first_name, u.last_name) == ("Grace", "Hopper")
        assert u.display_name == "Grace Hopper"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_name_split_api.py::TestApprovalCopiesNames -v`
Expected: FAIL — user has empty first/last (approval still sets `display_name`).

- [ ] **Step 3: Change `_create_user_with_role` signature**

In `backend/users/_helpers.py`, replace the `display_name` parameter with `first_name` / `last_name`:

```python
def _create_user_with_role(  # noqa: PLR0913
    phone: str,
    first_name: str,
    last_name: str,
    email: str | None,
    role_id: str | None,
    *,
    requesting_user: User,
    consent: ConsentTimestamps | None = None,
) -> tuple[User, str]:
```

In the `create_user(...)` call inside it, replace `display_name=display_name` with:

```python
        first_name=first_name,
        last_name=last_name,
```

(`display_name` is derived by `User.save()`.)

- [ ] **Step 4: Update all call sites**

Grep and update each caller:

Run: `cd backend && grep -rn "_create_user_with_role(" --include=*.py`

- `backend/users/_management.py:62` — pass `data.first_name, data.last_name` (from `UserCreateIn`).
- `backend/community/_join_request_approval.py:80` — pass `join_request.first_name, join_request.last_name`.

Update the two in-place mutation helpers in `_join_request_approval.py`
(`_reactivate_archived_user`, `_promote_non_member`): replace
`existing_user.display_name = join_request.display_name` (and the `user.` variant) with:

```python
    existing_user.first_name = join_request.first_name
    existing_user.last_name = join_request.last_name
```

and change their `update_fields` lists from `"display_name"` to `"first_name", "last_name"`.
(`display_name` is re-synced by `save()`, so it doesn't need to be in `update_fields` — but
since `save()` sets it, add `"display_name"` to `update_fields` too so the write persists.)

Concretely, `update_fields` becomes:

```python
        update_fields=[
            "archived_at",
            "needs_onboarding",
            "first_name",
            "last_name",
            "display_name",
            "guidelines_consent_at",
            "sms_consent_at",
        ]
```

- [ ] **Step 5a: Member self-patch (`_auth.py::_apply_me_patch`, lines ~254–257)**

Replace the `display_name` block. First/last win when sent; a bare `display_name` (old
client) is parsed. `save()` re-syncs `display_name`, so include it in `changed` so the
caller's `update_fields=changed` persists the synced value:

```python
    if payload.first_name is not None or payload.last_name is not None:
        if payload.first_name is not None:
            validate_display_name(payload.first_name)
            user.first_name = payload.first_name.strip()
        if payload.last_name is not None:
            validate_display_name(payload.last_name)
            user.last_name = payload.last_name.strip()
        changed.extend(["first_name", "last_name", "display_name"])
    elif payload.display_name is not None:
        validate_display_name(payload.display_name)
        first, last = parse_display_name(payload.display_name.strip())
        user.first_name, user.last_name = first, last
        changed.extend(["first_name", "last_name", "display_name"])
```

Add `from users._name_parsing import parse_display_name` to the imports.

Note on `validate_display_name` (`community/_shared.py`): it validates the allowed-character
set; a single-word last name and multi-word first name both pass it. Reuse as-is for
first/last. Do **not** widen or change it in PR1a.

- [ ] **Step 5b: Admin patch (`_management.py::_apply_user_patch`, lines ~292–294)**

```python
    if payload.first_name is not None or payload.last_name is not None:
        if payload.first_name is not None:
            validate_display_name(payload.first_name)
            user.first_name = payload.first_name.strip()
        if payload.last_name is not None:
            validate_display_name(payload.last_name)
            user.last_name = payload.last_name.strip()
    elif payload.display_name is not None:
        validate_display_name(payload.display_name)
        user.first_name, user.last_name = parse_display_name(payload.display_name.strip())
```

`_apply_user_patch` saves the whole user (grep the function to confirm it calls
`user.save()` without a restricted `update_fields`; if it uses `update_fields`, add
`"first_name"`, `"last_name"`, `"display_name"`). Add the `parse_display_name` import.

The audit-diff tuple at `_management.py:256` (`("phone_number", "display_name", "email")`)
can stay as-is for PR1a — `display_name` is still a real, synced column, so the diff remains
accurate.

- [ ] **Step 5c: Onboarding (`_auth.py::complete_onboarding`, lines ~419–421)**

```python
    if payload.first_name is not None or payload.last_name is not None:
        if payload.first_name is not None:
            validate_display_name(payload.first_name)
            user.first_name = payload.first_name.strip()
        if payload.last_name is not None:
            validate_display_name(payload.last_name)
            user.last_name = payload.last_name.strip()
    elif payload.display_name is not None:
        validate_display_name(payload.display_name)
        user.first_name, user.last_name = parse_display_name(payload.display_name.strip())
```

Confirm the surrounding `user.save(...)` includes `first_name`/`last_name`/`display_name` in
its `update_fields` if it uses one; otherwise `save()` persists all.

- [ ] **Step 5d: Admin create (`_management.py`, lines ~59–64)**

The current block calls `validate_display_name(payload.display_name)` then passes
`payload.display_name` to `_create_user_with_role`. Replace with:

```python
    if payload.first_name:
        validate_display_name(payload.first_name)
    if payload.last_name:
        validate_display_name(payload.last_name)
    first_name = payload.first_name
    last_name = payload.last_name
    if not first_name and payload.display_name:
        validate_display_name(payload.display_name)
        first_name, last_name = parse_display_name(payload.display_name)
```

Then pass `first_name, last_name` into `_create_user_with_role(...)` (positional args 2 and 3
per Task 6 Step 3's new signature). Add the `parse_display_name` import.

- [ ] **Step 5e: Join submit (`_join_request_submit.py`)**

Add `first_name`/`last_name` to the submit input schema (mirror `FieldLimit.FIRST_NAME` /
`LAST_NAME`), keeping `display_name` optional. When creating the `JoinRequest`, set
`first_name`/`last_name`; if only `display_name` came, parse it. The public form still sends
`display_name` until PR1b, so the parse fallback keeps it working.

- [ ] **Step 5f: Join resend (`_join_request_resend.py`, lines ~84,93)**

The resend rebuilds a `JoinRequest`-like payload from the original. Ensure it carries
`first_name`/`last_name` from the source request (add them to the dict at line ~84 and the
`JoinRequest.objects.create(...)`/message at line ~93). `display_name` may stay for the
message body — it renders from the synced column.

- [ ] **Step 6: Run the targeted + related suites**

Run: `cd backend && uv run pytest tests/test_name_split_api.py tests/test_user_management.py tests/test_onboarding.py tests/test_join_request_submission.py tests/test_join_request_conflicts.py -v`
Expected: PASS (fixtures updated in Task 7 if any fail on names — do Task 7 first if red).

- [ ] **Step 7: Commit**

```bash
printf 'feat(users): wire first/last through create/patch/onboarding/join flows (Issue 532)\n' > <SCRATCH>/msg.txt
git -C <WORKTREE> add backend/users/_helpers.py backend/users/_management.py backend/users/_auth.py backend/community/_join_request_approval.py backend/community/_join_request_submit.py backend/community/_join_request_resend.py backend/tests/test_name_split_api.py
git -C <WORKTREE> commit -F <SCRATCH>/msg.txt
```

---

## Task 7: Update shared test fixtures

**Files:**
- Modify: `backend/tests/conftest.py` (lines 88, 104, 122, 143, 161)

**Interfaces:**
- Produces: fixtures build users/join-requests with `first_name`/`last_name`.

- [ ] **Step 1: Update conftest fixtures**

Replace each `display_name="..."` in `conftest.py` with parsed first/last. Mapping:

- `display_name="Test Member"` → `first_name="Test", last_name="Member"`
- `display_name="Vettor"` → `first_name="Vettor"` (no last)
- `display_name="Admin User"` → `first_name="Admin", last_name="User"`
- `display_name=""` → `first_name=""` (legacy/blank-name fixture — keep it blank to preserve the onboarding-gate test case)
- `display_name="Sprout Seedling"` → `first_name="Sprout", last_name="Seedling"`

- [ ] **Step 2: Run the full backend suite**

Run: `cd backend && uv run pytest -q` (or `make agent-test`)
Expected: PASS. Investigate any failures referencing `display_name` — grep other test files for `display_name=` and update to first/last where they build users directly.

Run: `cd backend && grep -rn "display_name=" tests/`
Expected: only assertions that verify the synced `display_name` value remain; construction sites use first/last.

- [ ] **Step 3: Commit**

```bash
printf 'test(users): build fixtures with first/last name (Issue 532)\n' > <SCRATCH>/msg.txt
git -C <WORKTREE> add backend/tests/conftest.py
git -C <WORKTREE> commit -F <SCRATCH>/msg.txt
```

---

## Task 8: Full CI gate + regenerate OpenAPI types artifact

**Files:**
- Modify: `backend/openapi_schema.json` (regenerated)

- [ ] **Step 1: Regenerate the OpenAPI schema**

Run: `make frontend-types` (regenerates `frontend/src/api/types.gen.ts` + backend schema). Even though the frontend isn't consumed until PR1b, the generated types should reflect the new fields now so PR1b starts from a correct contract.

- [ ] **Step 2: Full CI**

Run: `make agent-ci`
Expected: PASS (ruff, ty, complexity, pytest). Fix anything red.

- [ ] **Step 3: Commit**

```bash
printf 'chore(api): regenerate OpenAPI types for first/last name fields (Issue 532)\n' > <SCRATCH>/msg.txt
git -C <WORKTREE> add backend/openapi_schema.json frontend/src/api/types.gen.ts
git -C <WORKTREE> commit -F <SCRATCH>/msg.txt
```

---

## Verification checklist (end of PR1a)

- [ ] `make agent-ci` green.
- [ ] New DB migrates cleanly from scratch (`make dev-db-reset`).
- [ ] `UserOut` responses contain `first_name`, `last_name`, `full_name`, **and** `display_name`.
- [ ] Creating a user / approving a join request populates first/last and `display_name == full_name`.
- [ ] Existing frontend (unchanged) still works — it reads `display_name`, which stays correct.
- [ ] `display_name` column still exists (dropped in PR1c).

## Notes for the executor

- `<WORKTREE>` = `/Users/leahpeker/development/pda/.claude/worktrees/feat-split-name-first-last`
- `<SCRATCH>` = the session scratchpad dir (write commit messages there, never `/tmp`).
- One `git` invocation per Bash call; use the literal absolute `-C` path.
- If the complexity checker flags `_create_user_with_role` (it already has `# noqa: PLR0913`), do not add new noqa without asking — the arg count is unchanged (swapped display_name for first+last is +1 arg; if it trips, ask the user).
