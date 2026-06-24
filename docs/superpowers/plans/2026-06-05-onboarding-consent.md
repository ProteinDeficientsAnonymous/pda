# Onboarding Consent (Guidelines + SMS) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Collect community-guidelines and SMS-policy consent inline during onboarding (conditionally, only when the user hasn't already consented), and add durable per-user SMS-consent tracking so consent is never silently dropped.

**Architecture:** Add a `User.sms_consent_at` field mirroring the existing `guidelines_consent_at`. Carry both consents from `JoinRequest` → `User` on approval (so join-form users arrive pre-consented). Extend the `complete-onboarding` endpoint to optionally stamp both consents, and render two conditional checkboxes in `OnboardingScreen` for any user still missing a consent (admin-created users, who have no JoinRequest). Fix the bug where onboarding redirected to `/guidelines` (a whitelisted read-only page) instead of routing through the gate.

**Tech Stack:** Django + Django Ninja (Pydantic schemas), pytest. React + TypeScript, react-hook-form + zod, Zustand, Vitest.

---

## Background / Why

A user created via **admin members → create user** has no `JoinRequest`, so they have no prior consent. After onboarding they were redirected to `/guidelines` — but `OnboardingGate` explicitly whitelists `/guidelines` from the consent redirect (so users can *read* the guidelines), so they were never bounced to `/consent` and never saw the acceptance checkbox.

Separately, SMS consent is only recorded on `JoinRequest.sms_consent_at` and never carried to the `User` — there is no `User.sms_consent_at` field at all. That is a compliance gap: there is no durable per-user record of SMS consent.

**Design decisions (locked with the user):**
- Consent is collected **inline in onboarding**, conditionally — checkboxes appear only for consents the user is missing.
- **Two separate checkboxes** (guidelines, SMS) for a clean consent record.
- Admin-created users consent at onboarding (they have no join form).
- The standalone `/consent` route + `ConsentScreen` + the guidelines gate are **kept** as the fallback for legacy users who must re-consent.
- **The SMS consent is recorded, NOT gated.** `GatedJWTAuth` will continue to hard-block only on `guidelines_consent_at is None`. We do NOT add an `sms_consent_at` hard block — legacy users without SMS consent must not be locked out of the app. (If the user later wants an SMS hard gate, that is a separate change.)

## Affected files

**Backend**
- `backend/users/models.py` — add `sms_consent_at` field (~line 61, next to `guidelines_consent_at`).
- `backend/users/migrations/0027_user_sms_consent_at.py` — **new** migration (nullable, no backfill).
- `backend/users/schemas.py` — `UserOut`: add `needs_sms_consent`; `OnboardingIn`: add `accept_guidelines` / `accept_sms` flags.
- `backend/users/_auth.py` — `complete_onboarding`: stamp the two consents when flagged.
- `backend/users/_helpers.py` — `_create_user_with_role`: accept optional `guidelines_consent_at` / `sms_consent_at` and pass to `create_user`.
- `backend/community/_join_requests.py` — approval: pass the `JoinRequest`'s consent timestamps into `_create_user_with_role` (both the new-user and the un-archive branch).

**Frontend**
- `frontend/src/models/user.ts` — add `needsSmsConsent` to `User`.
- `frontend/src/api/auth.ts` — `WireUser` + `mapUser`: map `needs_sms_consent`; `completeOnboarding`: send `accept_guidelines` / `accept_sms`.
- `frontend/src/auth/store.ts` — widen `completeOnboarding` payload type.
- `frontend/src/screens/auth/OnboardingScreen.tsx` — conditional consent checkboxes; route via `postAuthRedirect` instead of hardcoded `/guidelines`.

**Tests**
- `backend/tests/test_onboarding.py` — consent-stamping cases.
- `backend/tests/test_join_request_management.py` — consent carried to user on approval.
- `frontend/src/screens/auth/OnboardingScreen.test.tsx` — **new** (or extend if present) conditional-checkbox behavior.

---

## Task 1: Add `User.sms_consent_at` field + migration

**Files:**
- Modify: `backend/users/models.py:61`
- Create: `backend/users/migrations/0027_user_sms_consent_at.py`

- [ ] **Step 1: Add the field**

In `backend/users/models.py`, directly after the `guidelines_consent_at` field (line ~61), add:

```python
    # PERSISTENT USER STATE: when this user last accepted the SMS messaging
    # policy. Null means they have never consented. Mirrors guidelines_consent_at
    # and is surfaced on /me/ as needs_sms_consent, but — unlike guidelines — is
    # NOT a hard gate (see config.auth.GatedJWTAuth): we record SMS consent, we
    # do not lock legacy users out for lacking it. Carried from JoinRequest on
    # approval, or stamped by complete_onboarding when collected inline.
    sms_consent_at = models.DateTimeField(null=True, blank=True)
```

- [ ] **Step 2: Generate the migration**

Run: `cd backend && uv run python manage.py makemigrations users`
Expected: creates `backend/users/migrations/0027_user_sms_consent_at.py` adding `sms_consent_at`. Confirm it has **no** `RunPython`/backfill — just `AddField` with `null=True, blank=True`.

- [ ] **Step 3: Apply the migration**

Run: `cd backend && uv run python manage.py migrate users`
Expected: `Applying users.0027_user_sms_consent_at... OK`

- [ ] **Step 4: Commit**

```bash
git add backend/users/models.py backend/users/migrations/0027_user_sms_consent_at.py
git commit -m "feat(users): add sms_consent_at field for durable per-user sms consent"
```

---

## Task 2: Surface `needs_sms_consent` on `UserOut`

**Files:**
- Modify: `backend/users/schemas.py` (`UserOut` class + `from_user`)
- Test: `backend/tests/test_onboarding.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_onboarding.py`:

```python
@pytest.mark.django_db
class TestSmsConsentSerialized:
    def test_me_reports_needs_sms_consent_when_null(self, api_client, needs_onboarding_user):
        from ninja_jwt.tokens import RefreshToken

        needs_onboarding_user.sms_consent_at = None
        needs_onboarding_user.save(update_fields=["sms_consent_at"])
        token = RefreshToken.for_user(needs_onboarding_user).access_token
        resp = api_client.get(
            "/api/auth/me/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        assert resp.status_code == 200, resp.content
        assert resp.json()["needs_sms_consent"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_onboarding.py::TestSmsConsentSerialized -v`
Expected: FAIL — `KeyError: 'needs_sms_consent'` (field not serialized yet).

- [ ] **Step 3: Add the field to `UserOut`**

In `backend/users/schemas.py`, in `class UserOut`, directly after `needs_guidelines_consent: bool = False`:

```python
    needs_sms_consent: bool = False
```

And in `UserOut.from_user`, directly after the `needs_guidelines_consent=...` line:

```python
            needs_sms_consent=user.sms_consent_at is None,
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_onboarding.py::TestSmsConsentSerialized -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/users/schemas.py backend/tests/test_onboarding.py
git commit -m "feat(users): expose needs_sms_consent on /me/"
```

---

## Task 3: Stamp consents in `complete_onboarding`

**Files:**
- Modify: `backend/users/schemas.py` (`OnboardingIn`)
- Modify: `backend/users/_auth.py` (`complete_onboarding`)
- Test: `backend/tests/test_onboarding.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_onboarding.py`:

```python
@pytest.mark.django_db
class TestOnboardingConsent:
    def test_accept_flags_stamp_both_consents(
        self, api_client, needs_onboarding_user, needs_onboarding_auth_headers
    ):
        needs_onboarding_user.guidelines_consent_at = None
        needs_onboarding_user.sms_consent_at = None
        needs_onboarding_user.save(
            update_fields=["guidelines_consent_at", "sms_consent_at"]
        )
        resp = api_client.post(
            "/api/auth/complete-onboarding/",
            data={
                "new_password": "abcd1234ABCD!",
                "display_name": "Newby",
                "email": "newby@example.com",
                "accept_guidelines": True,
                "accept_sms": True,
            },
            content_type="application/json",
            **needs_onboarding_auth_headers,
        )
        assert resp.status_code == 200, resp.content
        body = resp.json()
        assert body["needs_guidelines_consent"] is False
        assert body["needs_sms_consent"] is False
        needs_onboarding_user.refresh_from_db()
        assert needs_onboarding_user.guidelines_consent_at is not None
        assert needs_onboarding_user.sms_consent_at is not None

    def test_omitted_flags_leave_consents_untouched(
        self, api_client, needs_onboarding_user, needs_onboarding_auth_headers
    ):
        needs_onboarding_user.guidelines_consent_at = None
        needs_onboarding_user.sms_consent_at = None
        needs_onboarding_user.save(
            update_fields=["guidelines_consent_at", "sms_consent_at"]
        )
        resp = api_client.post(
            "/api/auth/complete-onboarding/",
            data={
                "new_password": "abcd1234ABCD!",
                "display_name": "Newby",
                "email": "newby@example.com",
            },
            content_type="application/json",
            **needs_onboarding_auth_headers,
        )
        assert resp.status_code == 200, resp.content
        needs_onboarding_user.refresh_from_db()
        # Not flagged → not stamped. (Guidelines gate still blocks them elsewhere.)
        assert needs_onboarding_user.guidelines_consent_at is None
        assert needs_onboarding_user.sms_consent_at is None

    def test_accept_does_not_overwrite_existing_consent(
        self, api_client, needs_onboarding_user, needs_onboarding_auth_headers
    ):
        from django.utils import timezone

        earlier = timezone.now() - timezone.timedelta(days=30)
        needs_onboarding_user.guidelines_consent_at = earlier
        needs_onboarding_user.save(update_fields=["guidelines_consent_at"])
        resp = api_client.post(
            "/api/auth/complete-onboarding/",
            data={
                "new_password": "abcd1234ABCD!",
                "display_name": "Newby",
                "email": "newby@example.com",
                "accept_guidelines": True,
            },
            content_type="application/json",
            **needs_onboarding_auth_headers,
        )
        assert resp.status_code == 200, resp.content
        needs_onboarding_user.refresh_from_db()
        # Pre-existing consent is preserved, not re-stamped to "now".
        assert needs_onboarding_user.guidelines_consent_at == earlier
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_onboarding.py::TestOnboardingConsent -v`
Expected: FAIL — `accept_guidelines` / `accept_sms` are not accepted by the schema (or ignored), so consents stay null / the asserts fail.

- [ ] **Step 3: Add flags to `OnboardingIn`**

In `backend/users/schemas.py`, in `class OnboardingIn`, after the `email: OptionalEmail = None` line:

```python
    # Inline consent collected during onboarding for users with no prior consent
    # (admin-created accounts have no JoinRequest). Each flag stamps the matching
    # *_consent_at only when True AND the user hasn't already consented — so an
    # existing timestamp is never overwritten. Omitted/False = leave as-is.
    accept_guidelines: bool = False
    accept_sms: bool = False
```

- [ ] **Step 4: Stamp consents in `complete_onboarding`**

In `backend/users/_auth.py`, in `complete_onboarding`, immediately **before** `user.save()` (after `user.needs_password_reset = False`):

```python
    if payload.accept_guidelines and user.guidelines_consent_at is None:
        user.guidelines_consent_at = timezone.now()
    if payload.accept_sms and user.sms_consent_at is None:
        user.sms_consent_at = timezone.now()
```

(`user.save()` without `update_fields` already persists every changed field, so no field-list change is needed. `timezone` is already imported in this module.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_onboarding.py::TestOnboardingConsent -v`
Expected: PASS (all three)

- [ ] **Step 6: Commit**

```bash
git add backend/users/schemas.py backend/users/_auth.py backend/tests/test_onboarding.py
git commit -m "feat(auth): stamp guidelines+sms consent inline during onboarding"
```

---

## Task 4: Carry JoinRequest consent → User on approval

**Files:**
- Modify: `backend/users/_helpers.py` (`_create_user_with_role`)
- Modify: `backend/community/_join_requests.py` (approval handler, both branches)
- Test: `backend/tests/test_join_request_management.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_join_request_management.py` (mirror the file's existing fixtures/imports for an approver with `APPROVE_JOIN_REQUESTS`; adapt the helper names to those already in the file):

```python
@pytest.mark.django_db
class TestApprovalCarriesConsent:
    def test_new_user_inherits_join_request_consent(
        self, api_client, approver_headers
    ):
        from django.utils import timezone
        from community.models import JoinRequest, JoinRequestStatus
        from users.models import User

        jr = JoinRequest.objects.create(
            display_name="Consenter",
            phone_number="+12025550701",
            email="consenter@example.com",
            sms_consent_at=timezone.now(),
            guidelines_consent_at=timezone.now(),
        )
        resp = api_client.post(
            f"/api/community/join-requests/{jr.id}/status/",
            data={"status": JoinRequestStatus.APPROVED},
            content_type="application/json",
            **approver_headers,
        )
        assert resp.status_code == 200, resp.content
        user = User.objects.get(phone_number="+12025550701")
        assert user.guidelines_consent_at is not None
        assert user.sms_consent_at is not None
```

> NOTE: confirm the exact approval URL and the approver-headers fixture name by reading the top of `backend/tests/test_join_request_management.py`. The route is `update_join_request_status` (PATCH/POST to the join-requests status endpoint). Use whatever pattern the existing approval tests in that file already use rather than inventing a fixture.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_join_request_management.py::TestApprovalCarriesConsent -v`
Expected: FAIL — `user.guidelines_consent_at is None` (consent is dropped on creation today).

- [ ] **Step 3: Extend `_create_user_with_role` to accept consent timestamps**

In `backend/users/_helpers.py`, change the signature of `_create_user_with_role` to add two keyword-only params, and pass them into `create_user`.

Signature (add after `requesting_user: User`):

```python
def _create_user_with_role(
    phone: str,
    display_name: str,
    email: str | None,
    role_id: str | None,
    *,
    requesting_user: User,
    guidelines_consent_at=None,
    sms_consent_at=None,
) -> tuple[User, str]:
```

In the `User.objects.create_user(...)` call inside that function, add the two fields:

```python
    user = User.objects.create_user(
        phone_number=validated_phone,
        display_name=display_name,
        email=normalized_email,
        needs_onboarding=True,
        guidelines_consent_at=guidelines_consent_at,
        sms_consent_at=sms_consent_at,
    )
```

- [ ] **Step 4: Pass JoinRequest consent at the approval call site**

In `backend/community/_join_requests.py`, in `update_join_request_status`, the new-user branch — change the `_create_user_with_role(...)` call to pass the join request's timestamps:

```python
            _, magic_token = _create_user_with_role(
                join_request.phone_number,
                join_request.display_name,
                join_request.email,
                None,
                requesting_user=request.auth,
                guidelines_consent_at=join_request.guidelines_consent_at,
                sms_consent_at=join_request.sms_consent_at,
            )
```

And in the **un-archive branch** (where an archived user is reactivated), stamp the reactivated user from the join request too. Replace that branch's body so it also carries consent:

```python
        elif existing_user.archived_at is not None:
            from users._helpers import _create_magic_token

            existing_user.archived_at = None
            existing_user.needs_onboarding = True
            existing_user.display_name = join_request.display_name
            if join_request.guidelines_consent_at is not None:
                existing_user.guidelines_consent_at = join_request.guidelines_consent_at
            if join_request.sms_consent_at is not None:
                existing_user.sms_consent_at = join_request.sms_consent_at
            existing_user.save(
                update_fields=[
                    "archived_at",
                    "needs_onboarding",
                    "display_name",
                    "guidelines_consent_at",
                    "sms_consent_at",
                ]
            )
            magic_token = _create_magic_token(existing_user)
            user_created = True
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_join_request_management.py::TestApprovalCarriesConsent -v`
Expected: PASS

- [ ] **Step 6: Run the full join + onboarding backend test files**

Run: `cd backend && uv run pytest tests/test_join_request_management.py tests/test_onboarding.py tests/test_accept_guidelines.py -v`
Expected: PASS (no regressions)

- [ ] **Step 7: Commit**

```bash
git add backend/users/_helpers.py backend/community/_join_requests.py backend/tests/test_join_request_management.py
git commit -m "fix(join): carry guidelines+sms consent from join request to user on approval"
```

---

## Task 5: Backend CI gate

**Files:** none (verification only)

- [ ] **Step 1: Run full backend CI**

Run: `make agent-ci`
Expected: PASS — ruff (lint+format), ty typecheck, pytest, complexity all green. Fix any failures before continuing.

---

## Task 6: Frontend — map `needsSmsConsent`

**Files:**
- Modify: `frontend/src/models/user.ts` (`User` interface)
- Modify: `frontend/src/api/auth.ts` (`WireUser`, `mapUser`)

- [ ] **Step 1: Add `needsSmsConsent` to the `User` interface**

In `frontend/src/models/user.ts`, directly after the `needsGuidelinesConsent: boolean;` field:

```typescript
  // True until the user accepts the sms messaging policy (sms_consent_at is null
  // server-side). Unlike guidelines this is NOT a hard gate — it is collected
  // inline during onboarding when missing, but never locks an existing user out.
  needsSmsConsent: boolean;
```

- [ ] **Step 2: Map it in the wire layer**

In `frontend/src/api/auth.ts`, add to `WireUser` (after `needs_guidelines_consent?: boolean;`):

```typescript
  needs_sms_consent?: boolean;
```

And in `mapUser` (after `needsGuidelinesConsent: u.needs_guidelines_consent ?? false,`):

```typescript
    needsSmsConsent: u.needs_sms_consent ?? false,
```

- [ ] **Step 3: Typecheck**

Run: `make agent-frontend-typecheck`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add frontend/src/models/user.ts frontend/src/api/auth.ts
git commit -m "feat(frontend): map needsSmsConsent from /me/"
```

---

## Task 7: Frontend — send consent flags from `completeOnboarding`

**Files:**
- Modify: `frontend/src/api/auth.ts` (`completeOnboarding`)
- Modify: `frontend/src/auth/store.ts` (`completeOnboarding` payload type, two places)

- [ ] **Step 1: Widen the api payload + send flags**

In `frontend/src/api/auth.ts`, update `completeOnboarding`:

```typescript
export async function completeOnboarding(payload: {
  newPassword: string;
  displayName?: string | undefined;
  email?: string | undefined;
  acceptGuidelines?: boolean | undefined;
  acceptSms?: boolean | undefined;
}): Promise<User> {
  const { data } = await apiClient.post<WireUser>('/api/auth/complete-onboarding/', {
    new_password: payload.newPassword,
    display_name: payload.displayName,
    email: payload.email,
    accept_guidelines: payload.acceptGuidelines ?? false,
    accept_sms: payload.acceptSms ?? false,
  });
  return mapUser(data);
}
```

- [ ] **Step 2: Widen the store payload type**

In `frontend/src/auth/store.ts`, the `completeOnboarding` signature in the `AuthState` interface (around line 32):

```typescript
  completeOnboarding: (payload: {
    newPassword: string;
    displayName?: string | undefined;
    email?: string | undefined;
    acceptGuidelines?: boolean | undefined;
    acceptSms?: boolean | undefined;
  }) => Promise<void>;
```

(The implementation `async completeOnboarding(payload) { ... }` passes `payload` straight through, so no body change is needed.)

- [ ] **Step 3: Typecheck**

Run: `make agent-frontend-typecheck`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/auth.ts frontend/src/auth/store.ts
git commit -m "feat(frontend): pass guidelines+sms consent flags through completeOnboarding"
```

---

## Task 8: Frontend — conditional consent checkboxes in OnboardingScreen

**Files:**
- Modify: `frontend/src/screens/auth/OnboardingScreen.tsx`
- Test: `frontend/src/screens/auth/OnboardingScreen.test.tsx` (create if absent)

- [ ] **Step 1: Write the failing test**

Create/extend `frontend/src/screens/auth/OnboardingScreen.test.tsx`. Mirror the existing auth-screen test setup in the repo (check `frontend/src/screens/auth/*.test.tsx` for the render+router+store-mock pattern and reuse it; do not invent a new harness). The behaviors to assert:

```typescript
// 1. When the user still needs both consents, both checkboxes render and the
//    submit button is disabled until BOTH are checked.
// 2. When the user already consented to both (needsGuidelinesConsent=false,
//    needsSmsConsent=false), NEITHER checkbox renders and submit is enabled
//    once the form fields are valid.
// 3. On submit with both checked, completeOnboarding is called with
//    acceptGuidelines: true and acceptSms: true.
```

Concrete assertions (adapt selectors to the shared harness):

```typescript
it('requires both consents when both are missing', async () => {
  // render with store user { needsGuidelinesConsent: true, needsSmsConsent: true }
  expect(screen.getByLabelText(/community guidelines/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/sms/i)).toBeInTheDocument();
  // fill name/email/password validly, leave boxes unchecked → submit disabled
  expect(screen.getByRole('button', { name: /continue/i })).toBeDisabled();
});

it('hides consent when the user already consented', () => {
  // render with store user { needsGuidelinesConsent: false, needsSmsConsent: false }
  expect(screen.queryByLabelText(/community guidelines/i)).not.toBeInTheDocument();
  expect(screen.queryByLabelText(/sms/i)).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && pnpm vitest run src/screens/auth/OnboardingScreen.test.tsx`
Expected: FAIL — no checkboxes exist yet.

- [ ] **Step 3: Implement the conditional checkboxes + correct redirect**

Replace `frontend/src/screens/auth/OnboardingScreen.tsx` with the version below. Key changes vs. current:
- read `needsGuidelinesConsent` / `needsSmsConsent` from the store user;
- render each checkbox only when its consent is missing;
- track checkbox state with `useState`; gate submit on any required-but-unchecked consent;
- pass `acceptGuidelines` / `acceptSms` to `completeOnboarding`;
- after success, route via `postAuthRedirect(updatedUser) ?? '/calendar'` instead of the hardcoded `/guidelines`.

```tsx
import { useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link, useNavigate } from 'react-router-dom';
import { z } from 'zod';
import { AuthLayout } from './AuthLayout';
import { Button } from '@/components/ui/Button';
import { PasswordField } from '@/components/ui/PasswordField';
import { TextField } from '@/components/ui/TextField';
import { useAuthStore } from '@/auth/store';
import { extractApiError } from '@/utils/errors';
import { postAuthRedirect } from '@/models/user';
import { passwordRule } from './passwordRule';
import { PasswordChecklist } from './PasswordChecklist';

const schema = z.object({
  displayName: z.string().min(1, 'name required').max(64),
  email: z.string().min(1, 'email required').pipe(z.email('not a valid email')),
  newPassword: passwordRule,
});

type FormValues = z.infer<typeof schema>;

export default function OnboardingScreen() {
  const completeOnboarding = useAuthStore((s) => s.completeOnboarding);
  // Prefill displayName for legacy users who were approved before email was
  // required — they already have a name on file and only need to add email
  // + set a password.
  const existingDisplayName = useAuthStore((s) => s.user?.displayName ?? '');
  // Consent is collected inline only for users who haven't consented yet —
  // admin-created accounts (no JoinRequest). Join-form users arrive consented,
  // so these are false and the checkboxes don't render.
  const needsGuidelines = useAuthStore((s) => s.user?.needsGuidelinesConsent ?? false);
  const needsSms = useAuthStore((s) => s.user?.needsSmsConsent ?? false);
  const navigate = useNavigate();
  const [serverError, setServerError] = useState<string | null>(null);
  const [guidelinesChecked, setGuidelinesChecked] = useState(false);
  const [smsChecked, setSmsChecked] = useState(false);

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { displayName: existingDisplayName, email: '', newPassword: '' },
  });
  const passwordValue = useWatch({ control, name: 'newPassword' });

  const consentBlocked = (needsGuidelines && !guidelinesChecked) || (needsSms && !smsChecked);

  async function onSubmit(values: FormValues) {
    setServerError(null);
    try {
      await completeOnboarding({
        displayName: values.displayName,
        email: values.email,
        newPassword: values.newPassword,
        acceptGuidelines: needsGuidelines ? guidelinesChecked : undefined,
        acceptSms: needsSms ? smsChecked : undefined,
      });
      const next = postAuthRedirect(useAuthStore.getState().user) ?? '/calendar';
      void navigate(next, { replace: true });
    } catch (err) {
      setServerError(extractApiError(err, "couldn't finish onboarding — try again"));
    }
  }

  return (
    <AuthLayout title="welcome 🌱" subtitle="set your display name and a password">
      <form onSubmit={(e) => void handleSubmit(onSubmit)(e)} className="flex flex-col gap-4">
        <TextField
          label="display name"
          autoComplete="name"
          {...register('displayName')}
          error={errors.displayName?.message}
        />
        <TextField
          label="email"
          type="email"
          autoComplete="email"
          {...register('email')}
          error={errors.email?.message}
        />
        <PasswordChecklist value={passwordValue} />
        <PasswordField
          label="password"
          autoComplete="new-password"
          {...register('newPassword')}
          error={errors.newPassword?.message}
        />
        {needsGuidelines ? (
          <label className="text-foreground flex items-start gap-2 text-sm leading-relaxed">
            <input
              type="checkbox"
              checked={guidelinesChecked}
              onChange={(e) => {
                setGuidelinesChecked(e.target.checked);
              }}
              className="mt-1"
            />
            <span>
              i have read and agree to the{' '}
              <Link to="/guidelines" target="_blank" className="text-brand-700 underline">
                community guidelines
              </Link>
            </span>
          </label>
        ) : null}
        {needsSms ? (
          <label className="text-foreground flex items-start gap-2 text-sm leading-relaxed">
            <input
              type="checkbox"
              checked={smsChecked}
              onChange={(e) => {
                setSmsChecked(e.target.checked);
              }}
              className="mt-1"
            />
            <span>
              i agree to the{' '}
              <Link to="/sms-policy" target="_blank" className="text-brand-700 underline">
                sms policy
              </Link>
            </span>
          </label>
        ) : null}
        {serverError ? (
          <p role="alert" className="text-destructive text-sm">
            {serverError}
          </p>
        ) : null}
        <Button type="submit" fullWidth disabled={isSubmitting || consentBlocked}>
          {isSubmitting ? 'saving…' : 'continue'}
        </Button>
      </form>
    </AuthLayout>
  );
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd frontend && pnpm vitest run src/screens/auth/OnboardingScreen.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/screens/auth/OnboardingScreen.tsx frontend/src/screens/auth/OnboardingScreen.test.tsx
git commit -m "fix(auth): collect consent inline in onboarding and route via postAuthRedirect"
```

---

## Task 9: Frontend CI gate

**Files:** none (verification only)

- [ ] **Step 1: Run frontend CI**

Run: `make agent-frontend-lint && make agent-frontend-typecheck && make agent-frontend-test`
Expected: all PASS. Fix any failures.

---

## Task 10: Full CI + manual smoke

**Files:** none (verification only)

- [ ] **Step 1: Full backend + frontend CI**

Run: `make agent-ci && make agent-frontend-lint && make agent-frontend-typecheck && make agent-frontend-test`
Expected: all green.

- [ ] **Step 2: Manual smoke (the bug scenario)**

1. `make dev`
2. Admin-create a user via members screen (no join form).
3. Log in as that user → land on `/onboarding`.
4. Verify BOTH consent checkboxes appear; submit is disabled until both checked.
5. Fill name/email/password, check both, submit.
6. Verify you land on `/calendar` (NOT stranded on `/guidelines`), and the app is usable (guidelines gate cleared).
7. Re-login a *join-form-approved* user (after Task 4) and confirm NO consent checkboxes appear in onboarding and they reach `/calendar`.

- [ ] **Step 3: Regenerate API types (if the project tracks them)**

Run: `make frontend-types`
Expected: `frontend/src/api/types.gen.ts` updates to include `needs_sms_consent` / the new `OnboardingIn` fields. Commit if changed:

```bash
git add frontend/src/api/types.gen.ts
git commit -m "chore(frontend): regenerate api types for sms consent"
```

---

## Self-Review Notes (carried from planning)

- **Spec coverage:** sms_consent_at field (T1), needs_sms_consent serialized (T2), inline stamping (T3), join→user carry incl. un-archive branch (T4), frontend mapping (T6), flag passthrough (T7), conditional UI + redirect fix (T8). The original reported bug (onboarding stranded on `/guidelines`) is fixed in T8 by routing via `postAuthRedirect`.
- **Not in scope (explicit):** No SMS hard gate in `GatedJWTAuth` — SMS consent is recorded, not enforced. `/consent` + `ConsentScreen` retained as the legacy re-consent fallback (unchanged).
- **Type consistency:** `accept_guidelines`/`accept_sms` (snake, backend) ↔ `acceptGuidelines`/`acceptSms` (camel, frontend); `needs_sms_consent` ↔ `needsSmsConsent`. `postAuthRedirect` reused (not re-implemented).
- **Open verification for executor:** confirm the approval endpoint URL + approver fixture in `test_join_request_management.py` (Task 4 Step 1) and the shared auth-screen test harness (Task 8 Step 1) before writing those tests — both noted inline.
