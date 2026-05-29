# onboarding profile step — design

**date:** 2026-05-29
**branch:** `feat/onboarding-profile-step`

## goal

Make first-login onboarding feel welcoming and nudge new members to add a profile photo and a short bio right away — without making either required. Today onboarding collects only display name, email, and password on a single screen.

## flow

`OnboardingScreen` becomes a two-step wizard driven by internal `step` state. No new routes.

### step 1 — required account setup ("welcome 🌱")

- Unchanged from today: display name, email, password fields with existing zod validation (`passwordRule`, `PasswordChecklist`).
- Primary button `continue` calls `completeOnboarding({ displayName, email, newPassword })`. This is the call that flips `needsOnboarding` → false on the backend.
- **Change:** on success, advance to step 2 instead of navigating to `/guidelines`.
- Server errors render in place exactly as they do now.

### step 2 — optional profile ("make it yours ✨")

- Encouraging subtitle, lowercase, e.g. *"add a photo and a few words so folks can put a face to your name — you can always do this later"*.
- **Avatar:** reuse the existing `AvatarUpload` component as-is. It uploads instantly on crop via the auth store. No changes to the shared component.
- **Photo-added confirmation:** below the avatar, the step-2 view renders a small `✓ photo added` line when `user.profilePhotoUrl` is set. This lives in the onboarding view only — `AvatarUpload` is not modified.
- **Bio:** optional multiline `TextField`, max 500 chars (matches backend `bio` limit). Empty is fine.
- Buttons:
  - `done` — if bio is non-empty, call `updateProfile({ bio })`; then navigate to `/guidelines`. (Photo is already saved.)
  - `do this later` — text link; navigates straight to `/guidelines` with no save.

## save behavior

| field | when saved | mechanism |
|-------|-----------|-----------|
| photo | instantly on crop | existing `AvatarUpload` → `uploadProfilePhoto` store action |
| bio | on `done` (if non-empty) | `updateProfile({ bio })` store action |

Neither field blocks reaching `/guidelines`. Both are skippable via `do this later`.

## why this shape

- **Reuse:** `AvatarUpload`, `TextField`, `AuthLayout`, `Button`, and the existing auth-store actions cover almost everything. Bio field mirrors the pattern already in `BioEditDialog`.
- **No backend changes:** `bio` (CharField max 500) and `profile_photo` (ImageField) already exist on the User model, are exposed in `UserOut`, and are writable via `PATCH /api/auth/me/` and `POST /api/auth/me/photo/`. After step 1 the user is authenticated, so uploads work.
- **Casing:** all user-facing copy stays lowercase per the frontend casing rule.

## files touched

- `frontend/src/screens/auth/OnboardingScreen.tsx`
  - Add `step` state (`'account' | 'profile'`).
  - Split rendering into two sub-views. Step 1 logic is unchanged except the success handler advances the step rather than navigating.
  - If the file grows past ~150 lines, extract the step-2 view into a sibling `OnboardingProfileStep.tsx` to respect the file-size rule.
- (Possibly) `frontend/src/screens/auth/OnboardingProfileStep.tsx` — extracted step-2 view if needed.

No backend, model, schema, or API-type changes.

## testing

- Existing onboarding tests must still pass for step 1 (name/email/password → `completeOnboarding`).
- Add coverage for: advancing to step 2 after successful account setup; `do this later` navigates to `/guidelines` without calling `updateProfile`; entering a bio and hitting `done` calls `updateProfile({ bio })` then navigates; `✓ photo added` appears once `profilePhotoUrl` is set.

## out of scope

- Reworking `AvatarUpload` to defer upload until "done".
- Adding a `photo_updated_at` field to the backend schema (separate known gap; not needed here).
- Any change to the password-reset (`/new-password`) flow.
