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
`frontend/screenshots/<shot-name>-light.png` and `<shot-name>-dark.png`.
`shot` sets both color schemes, turns CSS animations and transitions off, and
sets reduced motion. Wait for a heading that is absent while the page is loading.

Pass `{ themes: false }` only when the page ignores the app theme, such as
rendered email HTML.

No clocks, unread counts, or random seed text. Do not commit the PNG. Do not
use `toHaveScreenshot` or add another workflow. Do not add a fixture named
`use`; that name fails the hooks lint.

From `frontend/`: `pnpm test:visual`. A repeated `shot` or `screen` name fails that command.

Screens that share a visitor belong in one test, so login happens once. Build that
list with `screen()` from `frontend/visual/session.ts` and pass it to `shootAll`.

## Logged-in or first-login

Only if the screen needs the API. The Visual job already starts Postgres,
migrate, `createcachetable`, and uvicorn in the same step as `pnpm test:visual`.
Vite's `webServer` proxies `/api` to port 8000. Leave that job, `artifact-name`,
and `branch` as they are.

Add a scenario in `backend/community/management/commands/e2e_seed.py` with a
fixed phone, name, title, and an absolute `start_datetime`. Do not call
`_random_phone` or `_random_event`. Sign in like `frontend/e2e/rsvp-member.spec.ts`.

`postAuthRedirect` may land on `/new-password`, `/onboarding`, or `/consent`
before the target page. Seed a user past that gate, or drive the gate you
mean to shoot. `member` already has a password. First login is
`needs_onboarding=True`: name and email set goes to `/new-password`, otherwise
`/onboarding` (`frontend/src/models/user.ts`).
