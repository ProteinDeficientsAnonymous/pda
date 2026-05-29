# onboarding profile step implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the single-screen onboarding into a welcoming two-step wizard that nudges new members to add a profile photo and short bio (both optional) right after setting up their account.

**Architecture:** `OnboardingScreen` gains internal `step` state (`'account' | 'profile'`). Step 1 keeps today's required name/email/password form but advances to step 2 on success instead of navigating away. Step 2 is a new sibling component, `OnboardingProfileStep`, that reuses the existing `AvatarUpload` (instant upload) and `Textarea` (bio) components, saves bio via `updateProfile` on "done", and offers a "do this later" skip — both paths land on `/guidelines`. No backend changes; `bio` and `profile_photo` already exist and the user is authenticated after step 1.

**Tech Stack:** React + TypeScript, react-hook-form + zod, Zustand auth store, react-router, vitest + @testing-library/react.

**Spec:** `docs/superpowers/specs/2026-05-29-onboarding-profile-step-design.md`

---

## File structure

- **Modify** `frontend/src/screens/auth/OnboardingScreen.tsx` — add `step` state; on successful `completeOnboarding`, switch to step 2 rather than navigating; render `OnboardingProfileStep` when on step 2.
- **Create** `frontend/src/screens/auth/OnboardingProfileStep.tsx` — the optional profile step: `AvatarUpload`, `✓ photo added` indicator, bio `Textarea`, `done` + `do this later` buttons.
- **Modify** `frontend/src/screens/auth/OnboardingScreen.test.tsx` — keep step-1 tests passing (button stays `continue`; after submit, assert step-2 content appears) and add step-2 behavior tests.
- **Create** `frontend/src/screens/auth/OnboardingProfileStep.test.tsx` — unit tests for the step-2 component in isolation.

Splitting step 2 into its own file keeps both files well under the 300-line target and lets step 2 be tested in isolation.

---

## Task 1: Extract the step-2 profile component (`OnboardingProfileStep`)

Build the optional profile step as a standalone component first, test-driven, before wiring it into the wizard. It takes a single `onDone` callback (navigation is the parent's concern) so it's trivial to test.

**Files:**
- Create: `frontend/src/screens/auth/OnboardingProfileStep.tsx`
- Test: `frontend/src/screens/auth/OnboardingProfileStep.test.tsx`

**Reference — existing pieces this reuses (do not modify them):**
- `AvatarUpload` (`frontend/src/screens/settings/AvatarUpload.tsx`) — reads `useAuthStore(s => s.user)`, uploads instantly on crop. Pass `size="lg"`.
- `Textarea` (`frontend/src/components/ui/Textarea.tsx`) — props: `label`, `value`, `onChange`, `maxLength`, `rows`, `error?`, `hint?`.
- `Button` (`frontend/src/components/ui/Button.tsx`) — supports `fullWidth`, `variant`, `disabled`.
- Auth store action `updateProfile(patch: ProfileUpdate) => Promise<void>` where `ProfileUpdate` includes `bio?: string`.
- `extractApiError(err, fallback)` from `frontend/src/utils/errors`.
- Bio max length is **500** (matches backend `bio` CharField and `BioEditDialog`'s `MAX_BIO`).

- [ ] **Step 1: Write the failing test**

Create `frontend/src/screens/auth/OnboardingProfileStep.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { OnboardingProfileStep } from './OnboardingProfileStep';
import { useAuthStore } from '@/auth/store';
import type { User } from '@/models/user';

vi.mock('@/auth/store', () => ({
  useAuthStore: vi.fn(),
}));

// AvatarUpload pulls in image-crop/canvas machinery we don't need here; stub it.
vi.mock('@/screens/settings/AvatarUpload', () => ({
  AvatarUpload: () => <div data-testid="avatar-upload" />,
}));

const baseUser: User = {
  id: 'u1',
  phoneNumber: '+15551234567',
  displayName: 'Tester',
  email: 'tester@example.com',
  bio: '',
  isSuperuser: false,
  isStaff: false,
  needsOnboarding: false,
  needsPasswordReset: false,
  showPhone: false,
  showEmail: false,
  weekStart: 'sunday',
  calendarFeedScope: 'all',
  profilePhotoUrl: '',
  photoUpdatedAt: null,
  roles: [],
};

describe('OnboardingProfileStep', () => {
  const updateProfile = vi.fn();
  const onDone = vi.fn();

  function mockStore(user: User) {
    vi.mocked(useAuthStore).mockImplementation((selector) =>
      selector({ user, updateProfile } as never),
    );
  }

  beforeEach(() => {
    updateProfile.mockReset();
    onDone.mockReset();
    updateProfile.mockResolvedValue(undefined);
    mockStore(baseUser);
  });

  it('skips without saving when "do this later" is clicked', async () => {
    render(<OnboardingProfileStep onDone={onDone} />);
    await userEvent.click(screen.getByRole('button', { name: /do this later/i }));
    expect(updateProfile).not.toHaveBeenCalled();
    expect(onDone).toHaveBeenCalledTimes(1);
  });

  it('saves a non-empty bio then finishes when "done" is clicked', async () => {
    render(<OnboardingProfileStep onDone={onDone} />);
    await userEvent.type(screen.getByLabelText(/bio/i), 'i love tofu');
    await userEvent.click(screen.getByRole('button', { name: /^done$/i }));
    expect(updateProfile).toHaveBeenCalledWith({ bio: 'i love tofu' });
    expect(onDone).toHaveBeenCalledTimes(1);
  });

  it('finishes without calling updateProfile when bio is left empty', async () => {
    render(<OnboardingProfileStep onDone={onDone} />);
    await userEvent.click(screen.getByRole('button', { name: /^done$/i }));
    expect(updateProfile).not.toHaveBeenCalled();
    expect(onDone).toHaveBeenCalledTimes(1);
  });

  it('shows the "photo added" confirmation once a profile photo exists', () => {
    mockStore({ ...baseUser, profilePhotoUrl: 'https://example.com/p.png' });
    render(<OnboardingProfileStep onDone={onDone} />);
    expect(screen.getByText(/photo added/i)).toBeInTheDocument();
  });

  it('does not show the "photo added" confirmation when there is no photo', () => {
    render(<OnboardingProfileStep onDone={onDone} />);
    expect(screen.queryByText(/photo added/i)).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && pnpm test run src/screens/auth/OnboardingProfileStep.test.tsx`
Expected: FAIL — `Failed to resolve import './OnboardingProfileStep'` (module does not exist yet).

- [ ] **Step 3: Write the minimal implementation**

Create `frontend/src/screens/auth/OnboardingProfileStep.tsx`:

```tsx
import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Textarea } from '@/components/ui/Textarea';
import { AvatarUpload } from '@/screens/settings/AvatarUpload';
import { useAuthStore } from '@/auth/store';
import { extractApiError } from '@/utils/errors';

const MAX_BIO = 500;

interface Props {
  onDone: () => void;
}

export function OnboardingProfileStep({ onDone }: Props) {
  const user = useAuthStore((s) => s.user);
  const updateProfile = useAuthStore((s) => s.updateProfile);
  const [bio, setBio] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const hasPhoto = Boolean(user?.profilePhotoUrl);

  async function onFinish() {
    const trimmed = bio.trim();
    if (!trimmed) {
      onDone();
      return;
    }
    setError(null);
    setSaving(true);
    try {
      await updateProfile({ bio: trimmed });
      onDone();
    } catch (err) {
      setError(extractApiError(err, "couldn't save your bio — try again"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col items-center gap-2">
        <AvatarUpload size="lg" />
        {hasPhoto ? (
          <p className="text-foreground-tertiary text-sm">✓ photo added</p>
        ) : null}
      </div>
      <Textarea
        label="bio"
        value={bio}
        onChange={(e) => {
          setBio(e.target.value);
        }}
        maxLength={MAX_BIO}
        rows={4}
        hint="optional — a sentence or two about you"
      />
      {error ? (
        <p role="alert" className="text-destructive text-sm">
          {error}
        </p>
      ) : null}
      <Button type="button" fullWidth disabled={saving} onClick={() => void onFinish()}>
        {saving ? 'saving…' : 'done'}
      </Button>
      <button
        type="button"
        onClick={onDone}
        className="text-foreground-tertiary hover:text-foreground text-sm underline transition-colors"
      >
        do this later
      </button>
    </div>
  );
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd frontend && pnpm test run src/screens/auth/OnboardingProfileStep.test.tsx`
Expected: PASS — all 5 tests green.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/screens/auth/OnboardingProfileStep.tsx frontend/src/screens/auth/OnboardingProfileStep.test.tsx
git commit -m "feat: add optional profile step component for onboarding"
```

---

## Task 2: Wire the two-step wizard into `OnboardingScreen`

Add `step` state to the existing screen. Step 1 keeps its current form and validation; on a successful `completeOnboarding` it advances to step 2 instead of navigating. Step 2 renders `OnboardingProfileStep`, whose `onDone` navigates to `/guidelines`.

**Files:**
- Modify: `frontend/src/screens/auth/OnboardingScreen.tsx`
- Test: `frontend/src/screens/auth/OnboardingScreen.test.tsx`

**Current behavior to preserve (from `OnboardingScreen.tsx`):**
- zod schema: `displayName` (min 1 / max 64), `email` (required + valid), `newPassword` (`passwordRule`).
- Prefills `displayName` from `useAuthStore(s => s.user?.displayName ?? '')`.
- `PasswordChecklist` driven by `useWatch` on `newPassword`.
- Submit button label is `continue`; on error, renders server error in a `role="alert"` paragraph.

- [ ] **Step 1: Update the existing tests for the two-step flow**

The two current tests assert nothing about post-submit navigation, so they keep working as-is for validation. Add step-transition + step-2 coverage. The `AuthLayout` and `OnboardingProfileStep` both render fine under `MemoryRouter`; stub `AvatarUpload` to avoid canvas/crop machinery.

Edit `frontend/src/screens/auth/OnboardingScreen.test.tsx`. Add the `AvatarUpload` mock alongside the existing mocks (after the `@/api/client` mock at the top):

```tsx
vi.mock('@/screens/settings/AvatarUpload', () => ({
  AvatarUpload: () => <div data-testid="avatar-upload" />,
}));
```

Then update `beforeEach` to also provide `updateProfile`, and add two tests. Replace the existing `beforeEach` block with:

```tsx
const updateProfile = vi.fn();

beforeEach(() => {
  completeOnboarding.mockReset();
  updateProfile.mockReset();
  updateProfile.mockResolvedValue(undefined);
  vi.mocked(useAuthStore).mockImplementation((selector) =>
    selector({ completeOnboarding, updateProfile, user: null } as never),
  );
});
```

Add these tests inside the `describe` block:

```tsx
it('advances to the profile step after successful account setup', async () => {
  completeOnboarding.mockResolvedValue(undefined);
  render(
    <MemoryRouter>
      <OnboardingScreen />
    </MemoryRouter>,
  );
  await userEvent.type(screen.getByLabelText(/display name/i), 'Tester');
  await userEvent.type(screen.getByLabelText(/^email$/i), 'tester@example.com');
  await userEvent.type(screen.getByLabelText(/^password$/i), 'abcd1234ABCD!');
  await userEvent.click(screen.getByRole('button', { name: /continue/i }));
  expect(await screen.findByRole('button', { name: /^done$/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /do this later/i })).toBeInTheDocument();
});

it('stays on the account step when account setup fails', async () => {
  completeOnboarding.mockRejectedValue(new Error('nope'));
  render(
    <MemoryRouter>
      <OnboardingScreen />
    </MemoryRouter>,
  );
  await userEvent.type(screen.getByLabelText(/display name/i), 'Tester');
  await userEvent.type(screen.getByLabelText(/^email$/i), 'tester@example.com');
  await userEvent.type(screen.getByLabelText(/^password$/i), 'abcd1234ABCD!');
  await userEvent.click(screen.getByRole('button', { name: /continue/i }));
  expect(await screen.findByText(/couldn't finish onboarding/i)).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: /^done$/i })).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run the tests to verify the new ones fail**

Run: `cd frontend && pnpm test run src/screens/auth/OnboardingScreen.test.tsx`
Expected: the two original validation tests PASS; the new `advances to the profile step` test FAILS (no `done` button appears — the screen still navigates instead of switching steps). The `stays on the account step` test should already pass.

- [ ] **Step 3: Implement the two-step wizard**

Replace the contents of `frontend/src/screens/auth/OnboardingScreen.tsx` with:

```tsx
import { useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useNavigate } from 'react-router-dom';
import { z } from 'zod';
import { AuthLayout } from './AuthLayout';
import { OnboardingProfileStep } from './OnboardingProfileStep';
import { Button } from '@/components/ui/Button';
import { PasswordField } from '@/components/ui/PasswordField';
import { TextField } from '@/components/ui/TextField';
import { useAuthStore } from '@/auth/store';
import { extractApiError } from '@/utils/errors';
import { passwordRule } from './passwordRule';
import { PasswordChecklist } from './PasswordChecklist';

const schema = z.object({
  displayName: z.string().min(1, 'name required').max(64),
  email: z.string().min(1, 'email required').pipe(z.email('not a valid email')),
  newPassword: passwordRule,
});

type FormValues = z.infer<typeof schema>;
type Step = 'account' | 'profile';

export default function OnboardingScreen() {
  const completeOnboarding = useAuthStore((s) => s.completeOnboarding);
  // Prefill displayName for legacy users who were approved before email was
  // required — they already have a name on file and only need to add email
  // + set a password.
  const existingDisplayName = useAuthStore((s) => s.user?.displayName ?? '');
  const navigate = useNavigate();
  const [step, setStep] = useState<Step>('account');
  const [serverError, setServerError] = useState<string | null>(null);

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

  async function onSubmit(values: FormValues) {
    setServerError(null);
    try {
      await completeOnboarding({
        displayName: values.displayName,
        email: values.email,
        newPassword: values.newPassword,
      });
      setStep('profile');
    } catch (err) {
      setServerError(extractApiError(err, "couldn't finish onboarding — try again"));
    }
  }

  if (step === 'profile') {
    return (
      <AuthLayout
        title="make it yours ✨"
        subtitle="add a photo and a few words so folks can put a face to your name — you can always do this later"
      >
        <OnboardingProfileStep onDone={() => void navigate('/guidelines', { replace: true })} />
      </AuthLayout>
    );
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
        {serverError ? (
          <p role="alert" className="text-destructive text-sm">
            {serverError}
          </p>
        ) : null}
        <Button type="submit" fullWidth disabled={isSubmitting}>
          {isSubmitting ? 'saving…' : 'continue'}
        </Button>
      </form>
    </AuthLayout>
  );
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd frontend && pnpm test run src/screens/auth/OnboardingScreen.test.tsx`
Expected: PASS — all four tests green.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/screens/auth/OnboardingScreen.tsx frontend/src/screens/auth/OnboardingScreen.test.tsx
git commit -m "feat: turn onboarding into a two-step wizard with optional profile step"
```

---

## Task 3: Full verification

Run the frontend CI gates over the whole suite to catch lint/prettier/type regressions the per-file test runs miss.

**Files:** none (verification only).

- [ ] **Step 1: Typecheck**

Run: `make agent-frontend-typecheck`
Expected: no errors. (Watch for: `Textarea` prop mismatch, `ProfileUpdate` shape, unused imports.)

- [ ] **Step 2: Lint + format check**

Run: `make agent-frontend-lint`
Expected: no errors. Fix any prettier/eslint findings, then re-run until clean.

- [ ] **Step 3: Full frontend test suite**

Run: `make agent-frontend-test`
Expected: entire vitest suite passes, including both onboarding test files.

- [ ] **Step 4: Commit any fixups**

Only if steps 1–3 required changes:

```bash
git add -A
git commit -m "chore: lint/type fixups for onboarding profile step"
```

---

## Manual verification (optional, after CI is green)

These confirm the real flow end-to-end; not required for the plan to be "done" but worth doing before opening the PR.

1. `make dev`, create/seed a user with `needs_onboarding=true`, log in → redirected to `/onboarding`.
2. Step 1: leave email blank → `email required`; fill name/email/valid password → `continue`.
3. Step 2: upload a photo → crop → `✓ photo added` appears; type a bio; `done` → lands on `/guidelines`; reopen profile/settings and confirm the photo and bio persisted.
4. Repeat as a second user but click `do this later` on step 2 → lands on `/guidelines` with no photo/bio set.

---

## Self-review notes

- **Spec coverage:** two-step wizard (Tasks 1–2), instant photo + `✓ photo added` indicator (Task 1), optional bio max 500 saved on done via `updateProfile` (Task 1), `do this later` skip (Task 1), advance-on-success / `/guidelines` target (Task 2), no backend changes (none in any task). All covered.
- **Copy/casing:** headings/buttons/body lowercase per `ui-copy-tone.md`; form labels keep the existing screen's lowercase style for consistency with the current onboarding form.
- **File size:** `OnboardingScreen.tsx` stays ~115 lines; `OnboardingProfileStep.tsx` ~70 lines — both well under target.
- **Type consistency:** `updateProfile({ bio })` matches `ProfileUpdate.bio?: string`; `onDone: () => void` used identically in component and tests; bio cap constant `MAX_BIO = 500` matches backend.
