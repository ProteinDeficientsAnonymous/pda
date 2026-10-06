---
name: add-visual-screenshot
description: >-
  Add a PDA screen to the visual regression workflow. Creates a Playwright spec
  under frontend/visual that writes a PNG for the Visual GitHub check, which
  comments before/after images on the PR when pixels differ. Use when
  onboarding a page to screenshot diffs, adding a logged-in or first-login
  shot, or extending the Visual workflow.
argument-hint: "<shot-name> <route>"
---

# Add a Visual Screenshot

Adds one screen to the existing Visual check. The check already screenshots
`/login`. A new screen is a new spec. Do not add a second workflow, a second
artifact, or Playwright's `toHaveScreenshot`.

Baselines are the `screenshots` Actions artifact from the last `main` run.
Changed images are embedded from the `ci__screenshots` branch. PNGs are
gitignored. `pnpm test:e2e` does not run these specs.

## Arguments

- `shot-name` — kebab-case file stem. `calendar` writes `frontend/screenshots/calendar.png`.
  Renaming a shot later looks like a delete plus a new image.
- `route` — path to open, e.g. `/calendar`.

## Pick the setup

- **Renders logged out, no API data** (the login page does this: a failed
  `/api/auth/refresh/` still shows the form). Add a spec only. The Visual job
  already starts Vite with no database.
- **Needs a logged-in user or API data.** Also boot Postgres and uvicorn in
  the Visual job, and seed **fixed** pixels. The current `e2e_seed` scenarios
  are the wrong data: phones, titles, and locations are random, and event
  start times are "now + 30 days", so the shot would differ on every run.

## Step 1 — Spec: `frontend/visual/<shot-name>.spec.ts`

Copy `frontend/visual/login.spec.ts`. `visual/**/*.ts` is already in
`frontend/tsconfig.e2e.json`.

```ts
import { expect, test } from '@playwright/test';

import { shot } from './shot';

test('calendar', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/calendar');
  await expect(page.getByRole('heading', { name: 'calendar' })).toBeVisible();
  await shot(page, 'calendar');
});
```

`shot` hides the caret and writes `frontend/screenshots/<shot-name>.png`.
Wait for a landmark that is absent while the page is still loading. Several
shots in one flow are fine (`login-phone`, `login-password`) as long as each
name stays stable.

Call `page.emulateMedia({ reducedMotion: 'reduce' })` in the spec. The
Playwright config cannot set it: `reducedMotion` is not in that version's
`use` options, and a custom `test` fixture trips `react-hooks/rules-of-hooks`
because the fixture callback is named `use`.

## Step 2 — Keep the pixels stable

Before writing the spec, look at the screen and remove or avoid:

- relative dates, "today", clocks, unread counts
- random or per-run seed text
- a blinking caret (already hidden) or a focus ring that depends on load order
- animations (the `emulateMedia` call above)

Freeze a clock with `page.clock` only when the screen itself renders time.
Prefer a screen state that has no time on it.

## Step 3 — Logged-in and first-login shots

Do this only when the screen needs the API.

1. Add a scenario in `backend/community/management/commands/e2e_seed.py` with
   fixed phone, name, title, and an absolute `start_datetime`. Do not call
   `_random_phone` or `_random_event`.
2. In the spec, import `seed` from `../e2e/fixtures` and sign in the way
   `frontend/e2e/rsvp-member.spec.ts` does. After submit, `postAuthRedirect`
   may send the user to `/new-password`, `/onboarding`, or `/consent` before
   the page you meant to shoot. Drive that gate on purpose, or seed a user
   who is past it. Do not screenshot whichever gate happens to appear.
3. First login after approval is not the `member` scenario. That user already
   has a password and `needs_onboarding=False`. A first-login user has
   `needs_onboarding=True` (see `frontend/src/models/user.ts`):
   - name and email already set → `/new-password`
   - either missing → `/onboarding`
4. Start Postgres, migrate, `createcachetable`, and uvicorn in
   `.github/workflows/visual.yml`, copying the e2e job in
   `.github/workflows/ci.yml`. Background processes die at the end of a step,
   so uvicorn and `pnpm test:visual` must share one step. Playwright's
   `webServer` starts Vite; Vite proxies `/api` to port 8000.

Leave `artifact-name: screenshots` and `branch: ci__screenshots` alone. Every
shot shares that one artifact and that one PR comment.

## Step 4 — Verify

From `frontend/`:

```bash
pnpm test:visual
```

Confirm `frontend/screenshots/<shot-name>.png` is the screen, not the boot
spinner. Do not commit the PNG.

## What the check does on the PR

`comment-mode: changes` plus `outdated-comment-action: update` edits the
existing Visual comment when `main` already has the `screenshots` artifact.
A push with no pixel diff rewrites that comment to resolved. A new filename
counts as a change until `main` has stored it.

Until `main` has the artifact, each push posts a new comment. That was only
true for the workflow's own introduction.

## Reference

| Concern | File |
|---------|------|
| Spec to copy | `frontend/visual/login.spec.ts` |
| PNG writer | `frontend/visual/shot.ts` |
| Playwright config | `frontend/playwright.visual.config.ts` |
| Local command | `pnpm test:visual` in `frontend/package.json` |
| Workflow | `.github/workflows/visual.yml` |
| Backend boot to copy | e2e job in `.github/workflows/ci.yml` |
| Sign-in steps | `frontend/e2e/rsvp-member.spec.ts` |
| Seed command | `backend/community/management/commands/e2e_seed.py` |
| First-login routing | `frontend/src/models/user.ts` (`postAuthRedirect`) |
