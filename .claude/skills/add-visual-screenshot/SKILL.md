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

Copy `frontend/visual/login.spec.ts` to `frontend/visual/<shot-name>.spec.ts`.
Change the route and `shot(page, '<shot-name>')`. That writes
`frontend/screenshots/<shot-name>.png`. Wait for a heading that is absent
while the page is loading.

Call `page.emulateMedia({ reducedMotion: 'reduce' })` in the spec. It cannot
live on the Playwright `use` config, and a custom fixture named `use` fails
the hooks lint.

No clocks, unread counts, or random seed text. Do not commit the PNG. Do not
use `toHaveScreenshot` or add another workflow.

From `frontend/`: `pnpm test:visual`. A repeated `shot` name fails that command.

## Logged-in or first-login

Only if the screen needs the API. The Visual job starts Vite and no database.

Add a scenario in `backend/community/management/commands/e2e_seed.py` with a
fixed phone, name, title, and an absolute `start_datetime`. Do not call
`_random_phone` or `_random_event`. Sign in like `frontend/e2e/rsvp-member.spec.ts`.

`postAuthRedirect` may land on `/new-password`, `/onboarding`, or `/consent`
before the target page. Seed a user past that gate, or drive the gate you
mean to shoot. `member` already has a password. First login is
`needs_onboarding=True`: name and email set goes to `/new-password`, otherwise
`/onboarding` (`frontend/src/models/user.ts`).

In `.github/workflows/visual.yml`, start Postgres, migrate, `createcachetable`,
and uvicorn in the same step as `pnpm test:visual` (see the e2e job in
`.github/workflows/ci.yml`). Vite's `webServer` proxies `/api` to port 8000.
Leave `artifact-name` and `branch` as they are.
