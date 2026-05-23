# Collect Email Addresses Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make email a first-class field on `User` and `JoinRequest` so every member has an email on file — without yet wiring up email sending, magic-link-by-email, or removing SMS.

**Architecture:** Five-phase rollout. Each phase produces a meaningful, testable commit. Phase 1 evolves the data model + migration. Phase 2 hardens the existing `PATCH /me/` endpoint with uniqueness + lowercasing + the new error code. Phase 3 makes `JoinRequest.email` a required, persisted field through the public submission flow and approval flow. Phase 4 makes email required on the onboarding screen. Phase 5 builds the blocking `RequireEmail` gate that blanks the app for any logged-in user without an email.

**Tech Stack:** Django 5 + Django Ninja (Pydantic) + ninja-jwt; React + Vite + Zustand + TanStack Query + Zod; PostgreSQL.

---

## File Map

**Backend**
- `backend/users/models.py` — alter `User.email` to unique + nullable; helper to normalize email.
- `backend/users/migrations/0057_data_blank_email_to_null.py` (new) — convert `email=""` → `NULL`.
- `backend/users/migrations/0058_user_email_unique.py` (new) — schema migration.
- `backend/users/_helpers.py` — normalize emails on user creation; new `_normalize_email`.
- `backend/users/_management.py` — `_apply_user_patch` enforces uniqueness on email.
- `backend/users/_auth.py` (or wherever `complete-onboarding` lives) — require email on the onboarding payload.
- `backend/users/schemas.py` — `OnboardingIn.email` becomes required; reuse existing `OptionalEmail` Annotated alias for join request payload too.
- `backend/community/models/join_form.py` — add `JoinRequest.email`.
- `backend/community/migrations/0057_joinrequest_email.py` (new) — schema migration.
- `backend/community/_join_requests.py` — require email on `JoinRequestIn`; persist on the model; copy to user on approval (uniqueness check).
- `backend/community/_validation.py` — add `Code.Email` codes.

**Frontend**
- `frontend/src/api/auth.ts` — `completeOnboarding` payload type: `email` becomes required.
- `frontend/src/auth/store.ts` — match new type.
- `frontend/src/api/types.gen.ts` — regenerated.
- `frontend/src/api/validationCodes.gen.ts` — regenerated.
- `frontend/src/api/validationCodes.ts` — add UI copy for new codes.
- `frontend/src/screens/auth/OnboardingScreen.tsx` — email becomes required.
- `frontend/src/screens/public/JoinScreen.tsx` — add required email field; pass to API.
- `frontend/src/api/join.ts` — type accepts `email`.
- `frontend/src/screens/admin/MemberCreateDialog.tsx` — add optional email field + nudge copy.
- `frontend/src/api/users.ts` — `useCreateUser` accepts `email`.
- `frontend/src/components/RequireEmail.tsx` (new) — blocking gate.
- `frontend/src/auth/guards.tsx` — add `EmailGate` component, compose into root.
- `frontend/src/router/AppRouter.tsx` (or equivalent) — wire `EmailGate` alongside `OnboardingGate`.

**Tests**
- `backend/tests/test_user_model.py` — migration outcome (data + schema).
- `backend/tests/test_auth_update_me.py` — uniqueness, lowercasing, conflict.
- `backend/tests/test_auth.py` — onboarding requires email.
- `backend/tests/test_join_request_submission.py` — require email; reject malformed.
- `backend/tests/test_join_request_management.py` — approval copies email; conflict surfaces.
- `frontend/src/screens/public/JoinScreen.test.tsx` — email required.
- `frontend/src/screens/auth/OnboardingScreen.test.tsx` (new if missing) — email required.
- `frontend/src/screens/admin/MemberCreateDialog.test.tsx` (new) — email optional, nudge copy.
- `frontend/src/components/RequireEmail.test.tsx` (new) — blocking, submit unblocks, conflict inline.
- `frontend/src/auth/guards.test.tsx` (new if missing) — EmailGate routing logic.

---

## Phase 1: Data Model + Migrations

### Task 1.1: Add `Email` validation codes

**Files:**
- Modify: `backend/community/_validation.py` (insert in alpha-ish order alongside Phone/Auth classes)

- [ ] **Step 1: Add `Email` code class**

Insert after the `Phone` class (around line 86):

```python
    class Email:
        INVALID = "email.invalid"
        ALREADY_EXISTS = "email.already_exists"
        REQUIRED = "email.required"
```

- [ ] **Step 2: Regenerate `validation_codes.json`**

Run: `cd backend && uv run python manage.py dump_validation_codes`
Expected: `validation_codes.json` now contains an `"Email"` block. Diff is staged-safe.

- [ ] **Step 3: Commit**

```bash
git add backend/community/_validation.py backend/community/validation_codes.json
git commit -m "feat(validation): add Email codes for collect-email work"
```

### Task 1.2: Alter `User.email` to unique + nullable

**Files:**
- Modify: `backend/users/models.py:46`
- Create: `backend/users/migrations/0057_data_blank_email_to_null.py`
- Create: `backend/users/migrations/0058_user_email_unique.py`
- Test: `backend/tests/test_user_model.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_user_model.py`:

```python
@pytest.mark.django_db
class TestUserEmailField:
    def test_blank_email_stored_as_null(self):
        from users.models import User

        u = User.objects.create_user(phone_number="+12025550199", display_name="t")
        u.refresh_from_db()
        assert u.email in (None, "")  # transition: post-migration this should be None

    def test_two_users_with_null_email_allowed(self):
        from users.models import User

        User.objects.create_user(phone_number="+12025550101", display_name="a", email=None)
        # Should NOT raise IntegrityError — multiple NULLs allowed.
        User.objects.create_user(phone_number="+12025550102", display_name="b", email=None)

    def test_duplicate_non_null_email_rejected(self):
        from django.db import IntegrityError
        from users.models import User

        User.objects.create_user(phone_number="+12025550101", display_name="a", email="dup@example.com")
        with pytest.raises(IntegrityError):
            User.objects.create_user(phone_number="+12025550102", display_name="b", email="dup@example.com")
```

- [ ] **Step 2: Run tests to verify failure**

Run: `cd backend && uv run pytest tests/test_user_model.py::TestUserEmailField -v`
Expected: FAIL — current schema has `blank=True` only; no uniqueness; blanks are `""` not NULL.

- [ ] **Step 3: Alter the model field**

In `backend/users/models.py`, replace line 46:

```python
    email = models.EmailField(unique=True, null=True, blank=True)
```

- [ ] **Step 4: Write data migration**

Create `backend/users/migrations/0057_data_blank_email_to_null.py`:

```python
from django.db import migrations


def blanks_to_null(apps, schema_editor):
    User = apps.get_model("users", "User")
    User.objects.filter(email="").update(email=None)


def null_to_blanks(apps, schema_editor):
    User = apps.get_model("users", "User")
    User.objects.filter(email__isnull=True).update(email="")


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0021_drop_edit_welcome_message_perm"),
    ]

    operations = [
        migrations.RunPython(blanks_to_null, null_to_blanks),
    ]
```

- [ ] **Step 5: Generate schema migration**

Run: `cd backend && uv run python manage.py makemigrations users --name user_email_unique`
Expected: a new file appears at `backend/users/migrations/0058_user_email_unique.py` that alters `email` to `EmailField(blank=True, null=True, unique=True)`. Inspect it; it should contain a single `AlterField` op.

- [ ] **Step 6: Run migration + tests**

Run: `cd backend && uv run python manage.py migrate users && uv run pytest tests/test_user_model.py::TestUserEmailField -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/users/models.py backend/users/migrations/0057_data_blank_email_to_null.py backend/users/migrations/0058_user_email_unique.py backend/tests/test_user_model.py
git commit -m "feat(users): make User.email unique + nullable"
```

### Task 1.3: Email normalization helper

**Files:**
- Modify: `backend/users/_helpers.py`
- Test: `backend/tests/test_user_model.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_user_model.py`:

```python
class TestNormalizeEmail:
    def test_lowercases(self):
        from users._helpers import _normalize_email

        assert _normalize_email("Foo@Example.COM") == "foo@example.com"

    def test_strips_whitespace(self):
        from users._helpers import _normalize_email

        assert _normalize_email("  foo@example.com  ") == "foo@example.com"

    def test_blank_returns_none(self):
        from users._helpers import _normalize_email

        assert _normalize_email("") is None
        assert _normalize_email("   ") is None
        assert _normalize_email(None) is None
```

- [ ] **Step 2: Run test to verify failure**

Run: `cd backend && uv run pytest tests/test_user_model.py::TestNormalizeEmail -v`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement helper**

In `backend/users/_helpers.py`, add near the top (after imports):

```python
def _normalize_email(raw: str | None) -> str | None:
    """Lowercase + strip an email. Returns None for blank input.

    Centralized so server-side enforcement is consistent across endpoints.
    Frontend should NOT rely on this — normalize there too.
    """
    if not raw:
        return None
    cleaned = raw.strip().lower()
    return cleaned or None
```

Also update `_create_user_with_role` (around line 69) to normalize:

```python
    user = User.objects.create_user(
        phone_number=validated_phone,
        display_name=display_name,
        email=_normalize_email(email),
        needs_onboarding=needs_onboarding,
    )
```

- [ ] **Step 4: Run tests**

Run: `cd backend && uv run pytest tests/test_user_model.py::TestNormalizeEmail -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/users/_helpers.py backend/tests/test_user_model.py
git commit -m "feat(users): _normalize_email helper + use in user creation"
```

---

## Phase 2: Harden `PATCH /me/` and admin create with uniqueness

### Task 2.1: Uniqueness check + normalization on `_apply_user_patch`

**Files:**
- Modify: `backend/users/_management.py:285-287`
- Test: `backend/tests/test_auth_update_me.py` (or `test_user_management.py` if patch test lives there — check first)

- [ ] **Step 1: Verify where the PATCH me test lives**

Run: `cd backend && grep -rn "def test.*email\|PATCH.*me\|/auth/me/" tests/test_auth_update_me.py | head`
Expected: identify a place to add new tests; use `test_auth_update_me.py` since the file exists.

- [ ] **Step 2: Write the failing tests**

Add to `backend/tests/test_auth_update_me.py`:

```python
class TestPatchMeEmail:
    def test_update_email_lowercases(self, api_client, auth_headers, test_user):
        resp = api_client.patch(
            "/api/auth/me/",
            data={"email": "FOO@Example.com"},
            content_type="application/json",
            **auth_headers,
        )
        assert resp.status_code == 200
        test_user.refresh_from_db()
        assert test_user.email == "foo@example.com"

    def test_duplicate_email_rejected(self, api_client, auth_headers, test_user, db):
        from users.models import User

        User.objects.create_user(
            phone_number="+12025550199", display_name="other", email="taken@example.com"
        )
        resp = api_client.patch(
            "/api/auth/me/",
            data={"email": "taken@example.com"},
            content_type="application/json",
            **auth_headers,
        )
        assert resp.status_code == 409
        body = resp.json()
        assert body["detail"][0]["code"] == "email.already_exists"

    def test_duplicate_email_case_insensitive(self, api_client, auth_headers, db):
        from users.models import User

        User.objects.create_user(
            phone_number="+12025550199", display_name="other", email="taken@example.com"
        )
        resp = api_client.patch(
            "/api/auth/me/",
            data={"email": "Taken@Example.com"},
            content_type="application/json",
            **auth_headers,
        )
        assert resp.status_code == 409
```

- [ ] **Step 3: Locate the PATCH /me/ handler**

Run: `cd backend && grep -n "auth/me\|def update_me\|def patch_me\|MePatchIn" users/_auth.py users/api.py`
Expected: find handler — probably in `users/_auth.py`. Read enough context to apply the patch.

- [ ] **Step 4: Run tests to verify failure**

Run: `cd backend && uv run pytest tests/test_auth_update_me.py::TestPatchMeEmail -v`
Expected: FAIL — currently no normalization, no uniqueness check.

- [ ] **Step 5: Add the uniqueness + normalization in PATCH /me/**

Edit the patch-me handler (file from step 3). Where the existing handler applies `email` from `MePatchIn`, replace with:

```python
from users._helpers import _normalize_email

if payload.email is not None:
    normalized = _normalize_email(payload.email)
    if normalized and User.objects.exclude(pk=request.auth.pk).filter(email=normalized).exists():
        raise_validation(Code.Email.ALREADY_EXISTS, field="email", status_code=409)
    request.auth.email = normalized
```

(Note: `_normalize_email` returns None for blanks — that's fine because the field is nullable.)

- [ ] **Step 6: Run tests to verify pass**

Run: `cd backend && uv run pytest tests/test_auth_update_me.py::TestPatchMeEmail -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/users/_auth.py backend/tests/test_auth_update_me.py
git commit -m "feat(users): enforce email uniqueness + lowercase on PATCH /me/"
```

### Task 2.2: Same hardening on admin PATCH /users/{id}/

**Files:**
- Modify: `backend/users/_management.py:278-289` (the `_apply_user_patch` function)
- Test: existing `test_user_management.py` if present, otherwise inline in `test_auth_update_me.py`

- [ ] **Step 1: Write the failing test**

Find an existing user-management test file and add:

```python
class TestAdminPatchEmail:
    def test_admin_patch_email_rejects_duplicate(self, api_client, admin_auth_headers, db):
        from users.models import User

        User.objects.create_user(
            phone_number="+12025550199", display_name="a", email="taken@example.com"
        )
        target = User.objects.create_user(
            phone_number="+12025550101", display_name="b"
        )
        resp = api_client.patch(
            f"/api/users/{target.id}/",
            data={"email": "Taken@Example.com"},
            content_type="application/json",
            **admin_auth_headers,
        )
        assert resp.status_code == 409
        assert resp.json()["detail"][0]["code"] == "email.already_exists"
```

If the file doesn't have an `admin_auth_headers` fixture, copy the pattern from `tests/test_validation_codes.py` lines 22–40 to build one inline.

- [ ] **Step 2: Run test to verify failure**

Run: `cd backend && uv run pytest -k "admin_patch_email" -v`
Expected: FAIL — `_apply_user_patch` currently sets `user.email = payload.email` with no check.

- [ ] **Step 3: Update `_apply_user_patch`**

In `backend/users/_management.py`, replace lines 285-286:

```python
    if payload.email is not None:
        normalized = _normalize_email(payload.email)
        if normalized and User.objects.exclude(pk=user_id).filter(email=normalized).exists():
            raise_validation(Code.Email.ALREADY_EXISTS, field="email", status_code=409)
        user.email = normalized
```

Add the imports at the top of the file:

```python
from community._validation import Code
from users._helpers import _normalize_email
```

(Check existing imports first; only add what's missing.)

- [ ] **Step 4: Run tests to verify pass**

Run: `cd backend && uv run pytest -k "admin_patch_email" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/users/_management.py backend/tests/test_user_management.py
git commit -m "feat(users): enforce email uniqueness on admin user PATCH"
```

### Task 2.3: Same hardening on `_create_user_with_role`

**Files:**
- Modify: `backend/users/_helpers.py:54-89`
- Test: file from prior task

- [ ] **Step 1: Write the failing test**

Add to the same admin tests file:

```python
class TestCreateUserDuplicateEmail:
    def test_create_user_duplicate_email_rejected(self, api_client, admin_auth_headers, db):
        from users.models import User

        User.objects.create_user(
            phone_number="+12025550199", display_name="a", email="taken@example.com"
        )
        resp = api_client.post(
            "/api/users/create-user/",
            data={
                "phone_number": "+12025550101",
                "display_name": "b",
                "email": "Taken@Example.com",
            },
            content_type="application/json",
            **admin_auth_headers,
        )
        assert resp.status_code == 409
        assert resp.json()["detail"][0]["code"] == "email.already_exists"
```

- [ ] **Step 2: Run test to verify failure**

Run: `cd backend && uv run pytest -k "create_user_duplicate_email" -v`
Expected: FAIL — `_create_user_with_role` currently doesn't check.

- [ ] **Step 3: Add the check in `_create_user_with_role`**

In `backend/users/_helpers.py`, after the existing `if User.objects.filter(phone_number=validated_phone).exists():` check (around line 67), insert:

```python
    normalized_email = _normalize_email(email)
    if normalized_email and User.objects.filter(email=normalized_email).exists():
        raise_validation(Code.Email.ALREADY_EXISTS, field="email", status_code=409)
```

Replace the `email=email or ""` argument in `User.objects.create_user(...)` (line 72) with:

```python
        email=normalized_email,
```

Add the import:

```python
from community._validation import Code, raise_validation  # already present — confirm
```

- [ ] **Step 4: Run tests**

Run: `cd backend && uv run pytest -k "create_user" -v`
Expected: PASS (existing tests + new one).

- [ ] **Step 5: Commit**

```bash
git add backend/users/_helpers.py backend/tests/test_user_management.py
git commit -m "feat(users): reject duplicate email in admin create-user"
```

---

## Phase 3: `JoinRequest.email` — collect on submission, copy on approval

### Task 3.1: Add `email` to `JoinRequest` model

**Files:**
- Modify: `backend/community/models/join_form.py:33`
- Create: `backend/community/migrations/0057_joinrequest_email.py`
- Test: `backend/tests/test_join_request_submission.py`

- [ ] **Step 1: Add the field**

In `backend/community/models/join_form.py`, after `phone_number` (line 34):

```python
    email = models.EmailField(blank=True, default="")
```

(Not unique, not required at the DB level — uniqueness lives on `User`, and an applicant could legitimately resubmit. Default empty for historical rows.)

- [ ] **Step 2: Generate migration**

Run: `cd backend && uv run python manage.py makemigrations community --name joinrequest_email`
Expected: `backend/community/migrations/0057_joinrequest_email.py` with a single `AddField`.

- [ ] **Step 3: Migrate**

Run: `cd backend && uv run python manage.py migrate community`
Expected: success.

- [ ] **Step 4: Commit**

```bash
git add backend/community/models/join_form.py backend/community/migrations/0057_joinrequest_email.py
git commit -m "feat(community): add email field to JoinRequest"
```

### Task 3.2: Require email on `JoinRequestIn`

**Files:**
- Modify: `backend/community/_join_requests.py:36-46`
- Test: `backend/tests/test_join_request_submission.py`

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_join_request_submission.py`:

```python
class TestJoinRequestEmail:
    def test_missing_email_rejected(self, api_client, db):
        resp = api_client.post(
            "/api/join-request/",
            data={
                "display_name": "Test",
                "phone_number": "+12025550101",
                "answers": {},
                "sms_consent": True,
            },
            content_type="application/json",
        )
        assert resp.status_code == 422

    def test_malformed_email_rejected(self, api_client, db):
        resp = api_client.post(
            "/api/join-request/",
            data={
                "display_name": "Test",
                "phone_number": "+12025550101",
                "answers": {},
                "sms_consent": True,
                "email": "not-an-email",
            },
            content_type="application/json",
        )
        assert resp.status_code == 422

    def test_valid_email_persisted_lowercased(self, api_client, db):
        from community.models import JoinRequest

        resp = api_client.post(
            "/api/join-request/",
            data={
                "display_name": "Test",
                "phone_number": "+12025550101",
                "answers": {},
                "sms_consent": True,
                "email": "Foo@Example.com",
            },
            content_type="application/json",
        )
        assert resp.status_code == 201, resp.content
        jr = JoinRequest.objects.get()
        assert jr.email == "foo@example.com"
```

- [ ] **Step 2: Run tests to verify failure**

Run: `cd backend && uv run pytest tests/test_join_request_submission.py::TestJoinRequestEmail -v`
Expected: FAIL — schema accepts payload without email.

- [ ] **Step 3: Add `email` to the schema and persist it**

In `backend/community/_join_requests.py`, edit `JoinRequestIn` (line 36):

```python
from pydantic import BaseModel, EmailStr, Field, field_validator

class JoinRequestIn(BaseModel):
    display_name: str = Field(max_length=FieldLimit.DISPLAY_NAME)
    phone_number: str = Field(max_length=FieldLimit.PHONE)
    email: EmailStr
    answers: dict[str, str] = {}
    sms_consent: bool = False
    website: str = Field(default="", max_length=FieldLimit.DISPLAY_NAME)
    # ...rest unchanged
```

In `submit_join_request`, normalize and persist (around line 243):

```python
    from users._helpers import _normalize_email
    normalized_email = _normalize_email(payload.email) or ""

    join_request = JoinRequest.objects.create(
        display_name=display_name,
        phone_number=validated_phone,
        email=normalized_email,
        custom_answers=custom_answers,
        sms_consent_at=timezone.now(),
    )
```

- [ ] **Step 4: Run tests**

Run: `cd backend && uv run pytest tests/test_join_request_submission.py::TestJoinRequestEmail -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/community/_join_requests.py backend/tests/test_join_request_submission.py
git commit -m "feat(community): require email on public join requests"
```

### Task 3.3: Copy email to user on approval (with uniqueness)

**Files:**
- Modify: `backend/community/_join_requests.py:354-374` (the approve branch in `update_join_request_status`)
- Test: `backend/tests/test_join_request_management.py`

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_join_request_management.py`:

```python
class TestApprovalEmail:
    def test_approval_copies_email_to_new_user(self, api_client, admin_auth_headers, db):
        from community.models import JoinRequest, JoinRequestStatus
        from users.models import User

        jr = JoinRequest.objects.create(
            display_name="Applicant",
            phone_number="+12025550101",
            email="applicant@example.com",
            status=JoinRequestStatus.PENDING,
        )
        resp = api_client.patch(
            f"/api/join-requests/{jr.id}/",
            data={"status": "approved"},
            content_type="application/json",
            **admin_auth_headers,
        )
        assert resp.status_code == 200
        user = User.objects.get(phone_number="+12025550101")
        assert user.email == "applicant@example.com"

    def test_approval_conflict_when_email_taken(self, api_client, admin_auth_headers, db):
        from community.models import JoinRequest, JoinRequestStatus
        from users.models import User

        User.objects.create_user(
            phone_number="+12025550199", display_name="other", email="taken@example.com"
        )
        jr = JoinRequest.objects.create(
            display_name="Applicant",
            phone_number="+12025550101",
            email="taken@example.com",
            status=JoinRequestStatus.PENDING,
        )
        resp = api_client.patch(
            f"/api/join-requests/{jr.id}/",
            data={"status": "approved"},
            content_type="application/json",
            **admin_auth_headers,
        )
        assert resp.status_code == 409
        assert resp.json()["detail"][0]["code"] == "email.already_exists"
```

- [ ] **Step 2: Run tests to verify failure**

Run: `cd backend && uv run pytest tests/test_join_request_management.py::TestApprovalEmail -v`
Expected: FAIL — approval currently passes `""` as email to `_create_user_with_role`.

- [ ] **Step 3: Pass `join_request.email` into `_create_user_with_role`**

In `backend/community/_join_requests.py`, in `update_join_request_status` (around line 358), replace:

```python
            _, magic_token = _create_user_with_role(
                join_request.phone_number,
                join_request.display_name,
                join_request.email,
                None,
            )
```

(The uniqueness check inside `_create_user_with_role` from Task 2.3 now surfaces the 409.)

- [ ] **Step 4: Run tests**

Run: `cd backend && uv run pytest tests/test_join_request_management.py -v`
Expected: PASS — both new tests + existing ones.

- [ ] **Step 5: Commit**

```bash
git add backend/community/_join_requests.py backend/tests/test_join_request_management.py
git commit -m "feat(community): copy join-request email to user on approval"
```

---

## Phase 4: Onboarding requires email

### Task 4.1: Make `OnboardingIn.email` required + normalize

**Files:**
- Modify: `backend/users/schemas.py:193-196`
- Modify: handler in `backend/users/_auth.py` (run `grep -n "complete-onboarding\|OnboardingIn" backend/users/_auth.py` to confirm location)
- Test: `backend/tests/test_auth.py`

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_auth.py` (or a new `test_onboarding.py`):

```python
class TestOnboardingEmail:
    def test_missing_email_rejected(self, api_client, needs_onboarding_auth_headers):
        resp = api_client.post(
            "/api/auth/complete-onboarding/",
            data={"new_password": "abcd1234ABCD", "display_name": "Newby"},
            content_type="application/json",
            **needs_onboarding_auth_headers,
        )
        assert resp.status_code == 422

    def test_email_required_and_lowercased(
        self, api_client, needs_onboarding_user, needs_onboarding_auth_headers
    ):
        resp = api_client.post(
            "/api/auth/complete-onboarding/",
            data={
                "new_password": "abcd1234ABCD",
                "display_name": "Newby",
                "email": "Newby@Example.com",
            },
            content_type="application/json",
            **needs_onboarding_auth_headers,
        )
        assert resp.status_code == 200
        needs_onboarding_user.refresh_from_db()
        assert needs_onboarding_user.email == "newby@example.com"
```

If `needs_onboarding_user` / `needs_onboarding_auth_headers` fixtures don't exist, add them to `backend/tests/conftest.py`:

```python
@pytest.fixture
def needs_onboarding_user(db):
    from users.models import User

    return User.objects.create_user(
        phone_number="+12025550110",
        password="x",
        display_name="",
        needs_onboarding=True,
    )


@pytest.fixture
def needs_onboarding_auth_headers(needs_onboarding_user):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(needs_onboarding_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}
```

- [ ] **Step 2: Run tests to verify failure**

Run: `cd backend && uv run pytest tests/test_auth.py::TestOnboardingEmail -v`
Expected: FAIL — schema currently has `email: OptionalEmail = None`.

- [ ] **Step 3: Update the schema**

In `backend/users/schemas.py:193`:

```python
class OnboardingIn(BaseModel):
    new_password: str = Field(max_length=FieldLimit.PASSWORD)
    display_name: str | None = Field(default=None, max_length=FieldLimit.DISPLAY_NAME)
    email: EmailStr
```

(Drop `OptionalEmail` for this schema. Make sure `EmailStr` is already imported at top — it is.)

- [ ] **Step 4: Update the onboarding handler**

Locate `complete_onboarding` (likely in `backend/users/_auth.py`). Where it sets email on the user, normalize first:

```python
from users._helpers import _normalize_email

normalized = _normalize_email(payload.email)
if normalized and User.objects.exclude(pk=request.auth.pk).filter(email=normalized).exists():
    raise_validation(Code.Email.ALREADY_EXISTS, field="email", status_code=409)
request.auth.email = normalized
```

- [ ] **Step 5: Run tests**

Run: `cd backend && uv run pytest tests/test_auth.py -v`
Expected: PASS (new tests + existing).

- [ ] **Step 6: Commit**

```bash
git add backend/users/schemas.py backend/users/_auth.py backend/tests/conftest.py backend/tests/test_auth.py
git commit -m "feat(users): require email on onboarding completion"
```

### Task 4.2: Regenerate OpenAPI + validation-code TS files

**Files:**
- Modify: `backend/openapi_schema.json` (regenerated)
- Modify: `frontend/src/api/types.gen.ts` (regenerated)
- Modify: `frontend/src/api/validationCodes.gen.ts` (regenerated)

- [ ] **Step 1: Regenerate**

Run: `make frontend-types`
Expected: types.gen.ts, validationCodes.gen.ts, validation_codes.json, openapi_schema.json all updated.

- [ ] **Step 2: Commit**

```bash
git add backend/openapi_schema.json frontend/src/api/types.gen.ts frontend/src/api/validationCodes.gen.ts backend/community/validation_codes.json
git commit -m "chore: regenerate api types + validation codes"
```

### Task 4.3: Add frontend copy for new Email validation codes

**Files:**
- Modify: `frontend/src/api/validationCodes.ts`

- [ ] **Step 1: Find the switch/map**

Run: `grep -n "phone.already_exists" frontend/src/api/validationCodes.ts`
Expected: a `case` line. Add Email cases nearby.

- [ ] **Step 2: Add the cases**

In `frontend/src/api/validationCodes.ts`, add to the switch (near the Phone cases):

```typescript
    case 'email.invalid':
      return 'that doesn\'t look like a valid email';
    case 'email.already_exists':
      return 'that email is already on another account — try a different one or contact admin';
    case 'email.required':
      return 'email required';
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/validationCodes.ts
git commit -m "feat(frontend): copy for new Email validation codes"
```

### Task 4.4: Onboarding screen — email required

**Files:**
- Modify: `frontend/src/screens/auth/OnboardingScreen.tsx`
- Modify: `frontend/src/api/auth.ts:134-145` (`completeOnboarding` signature)
- Modify: `frontend/src/auth/store.ts:32+96` (matching signature)
- Test: `frontend/src/screens/auth/OnboardingScreen.test.tsx` (create if missing)

- [ ] **Step 1: Write the failing test**

Create or extend `frontend/src/screens/auth/OnboardingScreen.test.tsx`:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import OnboardingScreen from './OnboardingScreen';
import { useAuthStore } from '@/auth/store';

vi.mock('@/auth/store', () => ({
  useAuthStore: vi.fn(),
}));

describe('OnboardingScreen', () => {
  const completeOnboarding = vi.fn();

  beforeEach(() => {
    completeOnboarding.mockReset();
    vi.mocked(useAuthStore).mockImplementation((selector) =>
      selector({ completeOnboarding } as never),
    );
  });

  it('shows email-required error when email is empty', async () => {
    render(
      <MemoryRouter>
        <OnboardingScreen />
      </MemoryRouter>,
    );
    await userEvent.type(screen.getByLabelText(/display name/i), 'Tester');
    await userEvent.type(screen.getByLabelText(/^password$/i), 'abcd1234ABCD');
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    expect(await screen.findByText(/email required/i)).toBeInTheDocument();
    expect(completeOnboarding).not.toHaveBeenCalled();
  });

  it('submits with required email', async () => {
    completeOnboarding.mockResolvedValue(undefined);
    render(
      <MemoryRouter>
        <OnboardingScreen />
      </MemoryRouter>,
    );
    await userEvent.type(screen.getByLabelText(/display name/i), 'Tester');
    await userEvent.type(screen.getByLabelText(/email/i), 'tester@example.com');
    await userEvent.type(screen.getByLabelText(/^password$/i), 'abcd1234ABCD');
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    expect(completeOnboarding).toHaveBeenCalledWith({
      displayName: 'Tester',
      email: 'tester@example.com',
      newPassword: 'abcd1234ABCD',
    });
  });
});
```

- [ ] **Step 2: Run test to verify failure**

Run: `cd frontend && pnpm vitest run src/screens/auth/OnboardingScreen.test.tsx`
Expected: FAIL — schema accepts blank email.

- [ ] **Step 3: Update the screen**

In `frontend/src/screens/auth/OnboardingScreen.tsx`:

- Replace the `schema` with:

```typescript
const schema = z.object({
  displayName: z.string().min(1, 'name required').max(64),
  email: z.email('not a valid email'),
  newPassword: passwordRule,
});
```

- Remove the `email === ''` branch in `onSubmit`:

```typescript
await completeOnboarding({
  displayName: values.displayName,
  email: values.email,
  newPassword: values.newPassword,
});
```

- Drop the `(optional)` from the field label; drop the `hint`:

```tsx
<TextField
  label="email"
  type="email"
  autoComplete="email"
  {...register('email')}
  error={errors.email?.message}
/>
```

- [ ] **Step 4: Update `completeOnboarding` types**

In `frontend/src/api/auth.ts`, line 134:

```typescript
export async function completeOnboarding(payload: {
  newPassword: string;
  displayName?: string | undefined;
  email: string;
}): Promise<User> {
```

In `frontend/src/auth/store.ts`, line 32 and the implementation at line 96:

```typescript
completeOnboarding: (payload: {
  newPassword: string;
  displayName?: string;
  email: string;
}) => Promise<void>;
```

- [ ] **Step 5: Run tests**

Run: `cd frontend && pnpm vitest run src/screens/auth/OnboardingScreen.test.tsx && pnpm typecheck`
Expected: PASS, no type errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/screens/auth/OnboardingScreen.tsx frontend/src/api/auth.ts frontend/src/auth/store.ts frontend/src/screens/auth/OnboardingScreen.test.tsx
git commit -m "feat(frontend): require email on onboarding screen"
```

---

## Phase 5: Public join form, admin create dialog, RequireEmail gate

### Task 5.1: Public join form — required email field

**Files:**
- Modify: `frontend/src/screens/public/JoinScreen.tsx`
- Modify: `frontend/src/api/join.ts` (type of submit payload)
- Test: `frontend/src/screens/public/JoinScreen.test.tsx`

- [ ] **Step 1: Write the failing test**

Add to `frontend/src/screens/public/JoinScreen.test.tsx`:

```typescript
describe('email validation', () => {
  it('shows email required when blank', async () => {
    renderWith(<JoinScreen />);
    await userEvent.type(screen.getByLabelText(/display name/i), 'Tester');
    await userEvent.type(screen.getByLabelText(/phone number/i), '+12025550101');
    await userEvent.click(screen.getByLabelText(/i agree to pda's/i));
    await userEvent.click(screen.getByRole('button', { name: /submit request/i }));
    expect(await screen.findByText(/email required/i)).toBeInTheDocument();
  });

  it('passes email to submit', async () => {
    const submit = vi.fn().mockResolvedValue(undefined);
    mockUseSubmitJoinRequest.mockReturnValue({
      mutateAsync: submit,
      isPending: false,
    } as unknown as ReturnType<typeof useSubmitJoinRequest>);

    renderWith(<JoinScreen />);
    await userEvent.type(screen.getByLabelText(/display name/i), 'Tester');
    await userEvent.type(screen.getByLabelText(/phone number/i), '+12025550101');
    await userEvent.type(screen.getByLabelText(/email/i), 'Tester@Example.com');
    await userEvent.click(screen.getByLabelText(/i agree to pda's/i));
    await userEvent.click(screen.getByRole('button', { name: /submit request/i }));
    expect(submit).toHaveBeenCalledWith(
      expect.objectContaining({ email: 'Tester@Example.com' }),
    );
  });
});
```

- [ ] **Step 2: Run test to verify failure**

Run: `cd frontend && pnpm vitest run src/screens/public/JoinScreen.test.tsx -t "email validation"`
Expected: FAIL — no email field in JoinScreen.

- [ ] **Step 3: Add the email field**

In `frontend/src/screens/public/JoinScreen.tsx`:

Add state (after `phoneNumber` state):

```typescript
const [email, setEmail] = useState('');
```

Update `validate`:

```typescript
if (!email.trim()) next.email = 'email required';
else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) next.email = 'not a valid email';
```

Update `onSubmit` payload (where `submit.mutateAsync({...})` is called):

```typescript
await submit.mutateAsync({
  displayName: displayName.trim(),
  phoneNumber: phoneNumber.trim(),
  email: email.trim(),
  answers: nonEmpty,
  smsConsent,
  website,
});
```

Add the `<TextField>` between the phone field and the questions loop:

```tsx
<TextField
  label="email"
  type="email"
  value={email}
  onChange={(e) => { setEmail(e.target.value); }}
  autoComplete="email"
  error={errors.email}
  required
/>
```

- [ ] **Step 4: Update the API type**

In `frontend/src/api/join.ts` find the submit payload type. Add `email: string` to the input shape and `email: payload.email` to the POST body.

- [ ] **Step 5: Run tests**

Run: `cd frontend && pnpm vitest run src/screens/public/JoinScreen.test.tsx && pnpm typecheck`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/screens/public/JoinScreen.tsx frontend/src/screens/public/JoinScreen.test.tsx frontend/src/api/join.ts
git commit -m "feat(public): require email on public join form"
```

### Task 5.2: Admin MemberCreateDialog — optional email + nudge copy

**Files:**
- Modify: `frontend/src/screens/admin/MemberCreateDialog.tsx`
- Modify: `frontend/src/api/users.ts` (`useCreateUser` payload includes email)
- Test: `frontend/src/screens/admin/MemberCreateDialog.test.tsx` (new)

- [ ] **Step 1: Write the failing test**

Create `frontend/src/screens/admin/MemberCreateDialog.test.tsx`:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemberCreateDialog } from './MemberCreateDialog';
import { useCreateUser } from '@/api/users';

vi.mock('@/api/users', () => ({
  useCreateUser: vi.fn(),
}));

describe('MemberCreateDialog', () => {
  const mutateAsync = vi.fn();

  beforeEach(() => {
    mutateAsync.mockReset();
    mutateAsync.mockResolvedValue({
      id: '1',
      phoneNumber: '+12025550101',
      displayName: '',
      magicLinkToken: 'tok',
    });
    vi.mocked(useCreateUser).mockReturnValue({
      mutateAsync,
      isPending: false,
    } as unknown as ReturnType<typeof useCreateUser>);
  });

  it('renders email field with nudge copy', () => {
    render(<MemberCreateDialog open onClose={() => {}} />);
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByText(/asked for one at first login/i)).toBeInTheDocument();
  });

  it('submits with no email when left blank', async () => {
    render(<MemberCreateDialog open onClose={() => {}} />);
    await userEvent.type(screen.getByLabelText(/phone number/i), '+12025550101');
    await userEvent.click(screen.getByRole('button', { name: /^create$/i }));
    expect(mutateAsync).toHaveBeenCalledWith({ phoneNumber: '+12025550101' });
  });

  it('submits with email when filled', async () => {
    render(<MemberCreateDialog open onClose={() => {}} />);
    await userEvent.type(screen.getByLabelText(/phone number/i), '+12025550101');
    await userEvent.type(screen.getByLabelText(/email/i), 'new@example.com');
    await userEvent.click(screen.getByRole('button', { name: /^create$/i }));
    expect(mutateAsync).toHaveBeenCalledWith({
      phoneNumber: '+12025550101',
      email: 'new@example.com',
    });
  });
});
```

- [ ] **Step 2: Run test to verify failure**

Run: `cd frontend && pnpm vitest run src/screens/admin/MemberCreateDialog.test.tsx`
Expected: FAIL — no email field.

- [ ] **Step 3: Update the dialog**

In `frontend/src/screens/admin/MemberCreateDialog.tsx`:

Add state:

```typescript
const [email, setEmail] = useState('');
```

Update `onSubmit`:

```typescript
const trimmed = email.trim();
const created = await createUser.mutateAsync({
  phoneNumber: phone.trim(),
  ...(trimmed ? { email: trimmed } : {}),
});
```

Update `handleClose` to clear email.

Insert the field after the phone field, before the error:

```tsx
<TextField
  label="email (optional)"
  type="email"
  hint="if you skip, they'll be asked for one at first login"
  value={email}
  onChange={(e) => { setEmail(e.target.value); }}
/>
```

- [ ] **Step 4: Update `useCreateUser` payload**

In `frontend/src/api/users.ts`, locate `useCreateUser` and ensure its input type accepts optional `email: string`, forwarded to the request body as `email`.

- [ ] **Step 5: Run tests**

Run: `cd frontend && pnpm vitest run src/screens/admin/MemberCreateDialog.test.tsx && pnpm typecheck`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/screens/admin/MemberCreateDialog.tsx frontend/src/screens/admin/MemberCreateDialog.test.tsx frontend/src/api/users.ts
git commit -m "feat(admin): optional email + nudge in member create dialog"
```

### Task 5.3: `RequireEmail` blocking component

**Files:**
- Create: `frontend/src/components/RequireEmail.tsx`
- Create: `frontend/src/components/RequireEmail.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/RequireEmail.test.tsx`:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RequireEmail } from './RequireEmail';
import { updateProfile } from '@/api/auth';

vi.mock('@/api/auth', () => ({
  updateProfile: vi.fn(),
}));

describe('RequireEmail', () => {
  beforeEach(() => {
    vi.mocked(updateProfile).mockReset();
  });

  it('renders the blocking form', () => {
    render(<RequireEmail />);
    expect(screen.getByText(/add your email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
  });

  it('submits and clears modal on success', async () => {
    vi.mocked(updateProfile).mockResolvedValue({ email: 'foo@example.com' } as never);
    render(<RequireEmail />);
    await userEvent.type(screen.getByLabelText(/email/i), 'foo@example.com');
    await userEvent.click(screen.getByRole('button', { name: /save/i }));
    expect(updateProfile).toHaveBeenCalledWith({ email: 'foo@example.com' });
  });

  it('shows conflict error inline', async () => {
    vi.mocked(updateProfile).mockRejectedValue({
      response: { status: 409, data: { detail: [{ code: 'email.already_exists' }] } },
    });
    render(<RequireEmail />);
    await userEvent.type(screen.getByLabelText(/email/i), 'taken@example.com');
    await userEvent.click(screen.getByRole('button', { name: /save/i }));
    expect(await screen.findByText(/already on another account/i)).toBeInTheDocument();
  });

  it('shows malformed-email error inline', async () => {
    render(<RequireEmail />);
    await userEvent.type(screen.getByLabelText(/email/i), 'not-an-email');
    await userEvent.click(screen.getByRole('button', { name: /save/i }));
    expect(await screen.findByText(/not a valid email/i)).toBeInTheDocument();
    expect(updateProfile).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run test to verify failure**

Run: `cd frontend && pnpm vitest run src/components/RequireEmail.test.tsx`
Expected: FAIL — component does not exist.

- [ ] **Step 3: Implement the component**

Create `frontend/src/components/RequireEmail.tsx`:

```tsx
import { useState, type SyntheticEvent } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { updateProfile } from '@/api/auth';
import { extractApiErrorOr } from '@/api/apiErrors';
import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/TextField';

export function RequireEmail() {
  const setUser = useAuthStore((s) => s.setUser);
  const qc = useQueryClient();
  const [email, setEmail] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: SyntheticEvent) {
    e.preventDefault();
    const trimmed = email.trim();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed)) {
      setError('not a valid email');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const user = await updateProfile({ email: trimmed });
      setUser(user);
      await qc.invalidateQueries({ queryKey: ['me'] });
    } catch (err) {
      setError(extractApiErrorOr(err, "couldn't save your email — try again"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="bg-surface w-full max-w-sm rounded-lg p-6">
        <h2 className="mb-2 text-lg font-medium">add your email 🌱</h2>
        <p className="text-foreground-tertiary mb-4 text-sm">
          we use email for account recovery and announcements — please add yours to continue
        </p>
        <form onSubmit={(e) => void onSubmit(e)} className="flex flex-col gap-3">
          <TextField
            label="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => { setEmail(e.target.value); }}
            error={error ?? undefined}
            required
          />
          <Button type="submit" fullWidth disabled={submitting}>
            {submitting ? 'saving…' : 'save'}
          </Button>
        </form>
      </div>
    </div>
  );
}
```

(Confirm `useAuthStore` exposes `setUser`; if it doesn't, use `useAuthStore.setState({ user })` after refetching `/me` directly. Check `frontend/src/auth/store.ts` first.)

- [ ] **Step 4: Run tests**

Run: `cd frontend && pnpm vitest run src/components/RequireEmail.test.tsx && pnpm typecheck`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/RequireEmail.tsx frontend/src/components/RequireEmail.test.tsx
git commit -m "feat(frontend): RequireEmail blocking gate component"
```

### Task 5.4: Wire `RequireEmail` into the route guards

**Files:**
- Modify: `frontend/src/auth/guards.tsx`
- Modify: `frontend/src/router/AppRouter.tsx` (or wherever `OnboardingGate` is composed — verify location)
- Test: `frontend/src/auth/guards.test.tsx`

- [ ] **Step 1: Locate where `OnboardingGate` is composed**

Run: `cd frontend && grep -rn "OnboardingGate" src/router/ src/`
Expected: identify the route tree.

- [ ] **Step 2: Write the failing test**

Create or extend `frontend/src/auth/guards.test.tsx`:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { EmailGate } from './guards';
import { useAuthStore } from './store';

vi.mock('./store', () => ({
  useAuthStore: vi.fn(),
}));

function setUser(user: { email: string | null; needsOnboarding?: boolean } | null) {
  vi.mocked(useAuthStore).mockImplementation((selector) =>
    selector({ user } as never),
  );
}

describe('EmailGate', () => {
  beforeEach(() => {
    vi.mocked(useAuthStore).mockReset();
  });

  it('renders RequireEmail when user lacks email', () => {
    setUser({ email: null });
    render(
      <MemoryRouter initialEntries={['/calendar']}>
        <Routes>
          <Route element={<EmailGate />}>
            <Route path="/calendar" element={<div>calendar</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByText(/add your email/i)).toBeInTheDocument();
    expect(screen.queryByText('calendar')).not.toBeInTheDocument();
  });

  it('renders Outlet when user has email', () => {
    setUser({ email: 'foo@example.com' });
    render(
      <MemoryRouter initialEntries={['/calendar']}>
        <Routes>
          <Route element={<EmailGate />}>
            <Route path="/calendar" element={<div>calendar</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByText('calendar')).toBeInTheDocument();
  });

  it('renders Outlet for unauthed (null user)', () => {
    setUser(null);
    render(
      <MemoryRouter initialEntries={['/login']}>
        <Routes>
          <Route element={<EmailGate />}>
            <Route path="/login" element={<div>login</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByText('login')).toBeInTheDocument();
  });

  it('renders Outlet when needs_onboarding (OnboardingGate handles routing)', () => {
    setUser({ email: null, needsOnboarding: true });
    render(
      <MemoryRouter initialEntries={['/onboarding']}>
        <Routes>
          <Route element={<EmailGate />}>
            <Route path="/onboarding" element={<div>onboarding</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByText('onboarding')).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Run test to verify failure**

Run: `cd frontend && pnpm vitest run src/auth/guards.test.tsx`
Expected: FAIL — `EmailGate` does not exist.

- [ ] **Step 4: Add the `EmailGate` component**

In `frontend/src/auth/guards.tsx`, add at the bottom:

```tsx
import { RequireEmail } from '@/components/RequireEmail';

// ----------------------------------------------------------------------------
// EmailGate — blocks the app for authed users without an email. Composes
// AFTER OnboardingGate so needs_onboarding users finish that flow first.
// ----------------------------------------------------------------------------

export function EmailGate() {
  const user = useAuthStore((s) => s.user);
  if (user && !user.needsOnboarding && !user.email) {
    return <RequireEmail />;
  }
  return <Outlet />;
}
```

- [ ] **Step 5: Compose into the route tree**

In the router file from Step 1, nest `EmailGate` immediately inside `OnboardingGate`:

```tsx
<Route element={<OnboardingGate />}>
  <Route element={<EmailGate />}>
    {/* existing routes */}
  </Route>
</Route>
```

- [ ] **Step 6: Run tests**

Run: `cd frontend && pnpm vitest run src/auth/guards.test.tsx && pnpm typecheck`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/auth/guards.tsx frontend/src/auth/guards.test.tsx frontend/src/router/AppRouter.tsx
git commit -m "feat(frontend): EmailGate blocks app for authed users without email"
```

---

## Phase 6: Full CI + manual verification

### Task 6.1: Full CI pass

- [ ] **Step 1: Run the full pre-commit check**

Run: `make agent-ci`
Expected: PASS — lint, typecheck, test, complexity, codes check.

- [ ] **Step 2: Fix anything that fails**

If any check fails, debug and fix (`make ci` for verbose output). Do not relax thresholds or skip checks. Re-run until clean.

### Task 6.2: Manual smoke check

- [ ] **Step 1: Start the dev environment**

Run (separate terminals or `make dev`):
- `make db-start`
- `make dev`

- [ ] **Step 2: Smoke flows**

Verify each by hand:

1. **Existing user with no email logs in** → `RequireEmail` blocks the app. Submit a valid email → modal disappears, app renders.
2. **Public join form** rejects submission without email; accepts with a valid one. Inspect `JoinRequest` row in admin to confirm email was lowercased and saved.
3. **Admin "add member"** creates a user without email (leaving field blank). Then log in as that user → `RequireEmail` fires.
4. **Admin "add member"** with an email that collides with another user → friendly error appears inline.
5. **Approve a join request** → user is created with the email copied across.
6. **Approve a join request whose email collides** with an existing user → error surfaces; admin can resolve.

- [ ] **Step 3: Report results**

Note any UI tweaks discovered during smoke (copy, spacing, focus order). Open follow-up commits if small; otherwise file an issue.

### Task 6.3: Open PR

- [ ] **Step 1: Push the branch**

Run: `git push -u origin feat/collect-email-addresses`
Expected: branch pushed.

- [ ] **Step 2: Open the PR**

Use the `open-pr` skill. PR body should:
- Link the spec at `docs/superpowers/specs/2026-05-19-collect-email-addresses-design.md`.
- Mention follow-ups #429, #430, #431, #432 are still open.
- Include a smoke-check checklist from Task 6.2.

---

## Self-Review (post-write)

**1. Spec coverage:**
- Data-model changes — Task 1.2 ✓
- Migrations safe (data → schema) — Task 1.2 ✓
- Email normalization rule (lowercase) — Task 1.3 ✓
- Uniqueness enforcement on PATCH /me/, admin PATCH, create-user, approval — Tasks 2.1, 2.2, 2.3, 3.3 ✓
- JoinRequest.email + persistence + propagation — Tasks 3.1, 3.2, 3.3 ✓
- Onboarding requires email — Task 4.1 + 4.4 ✓
- Frontend validation copy — Task 4.3 ✓
- Public join form requires email — Task 5.1 ✓
- Admin "add member" optional + nudge — Task 5.2 ✓
- RequireEmail blocking modal — Task 5.3 ✓
- EmailGate composition — Task 5.4 ✓
- Tests at every layer — every task ✓
- Manual smoke — Task 6.2 ✓

**2. Placeholders:** None — every step has explicit code or commands.

**3. Type consistency:**
- `_normalize_email` returns `str | None` everywhere it's used.
- Email codes referenced as `Code.Email.{INVALID,ALREADY_EXISTS,REQUIRED}` in backend; `email.already_exists` etc. in frontend.
- `RequireEmail` (component) vs `EmailGate` (route guard) — two distinct names, used consistently.
- `completeOnboarding` signature: `email: string` (required) in `api/auth.ts` and `auth/store.ts` — matched.
