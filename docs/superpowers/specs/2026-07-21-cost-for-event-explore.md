# Explore: cost for event (#1045) — Findings

**Date:** 2026-07-21
**Issue:** https://github.com/ProteinDeficientsAnonymous/pda/issues/1045
**Branch / PR:** `explore-1045-cost-for-event`

## The ask

From the issue body, users should have to confirm they paid before an RSVP is finalized, when an event has a cost. The reporter sketched three flows, each ending in "link to payment method > did you pay? yes? > confirm rsvp":

1. **Signed-in member // non-member with a valid token** — rsvp button → payment step → confirm.
2. **Not-signed-in member** — rsvp button → phone number → sign in → payment step → confirm.
3. **Brand new person** — rsvp button → phone number → join form → payment step → confirm.

## What we found

**The payment data model and UI already exist end-to-end — this is a confirmation-gate feature, not a payment-data feature.**

`Event` already has `price`, `venmo_link`, `cashapp_link`, `zelle_info` (all optional/blank), added in migration `0026_event_cashapp_link_event_price_event_venmo_link_and_more.py`. Hosts already set these via the event form, they're already serialized in every Event schema, and `CostSection` already renders them as clickable payment links to signed-in/token viewers. None of that needs to be built.

What's missing is any concept of a **required confirmation** gating RSVP creation. There is no field on `EventRSVP` for it, no backend validation step for it, and no reusable "extra step before submit" UI pattern anywhere in the app — every existing multi-step flow (login, onboarding, the public RSVP form) is a bespoke local `useState` step machine, not a shared wizard component.

### The three flows map onto four distinct RSVP-mutation surfaces

The issue's three flows don't line up 1:1 with three components — they touch four:

- **Signed-in member AND non-member-with-token both go through `RsvpSection.tsx` → `RsvpBox.tsx`** (a single dialog, single submit — `RsvpBox`'s `confirm()` calls `onConfirm` immediately). Covering flow 1 is one change in one place.
- **Not-signed-in member** never actually submits an RSVP while unauthenticated — `PublicRsvpForm.tsx` sends them to `/login` (`navigate('/login', {state:{phone, redirect}})`) and after sign-in they land back on the event as an authed member, i.e. **flow 2 collapses into flow 1** once login completes. No separate payment step is needed for the pre-login half of this flow.
- **Brand new person** flows entirely through `PublicRsvpForm.tsx`'s `renderStep()` state machine (status picker → phone step → new-person form → single atomic `submitPublicRsvp` POST that creates the person and the RSVP together). The payment step has to be inserted as a new step in this machine, before the existing submit fires — the join+RSVP POST is atomic server-side, so there's no natural "confirm payment between join and RSVP" server round-trip; it's a client-side gate before one POST.
- **A fourth surface exists that the issue doesn't mention: `PublicRsvpCard.tsx`**, where a returning token holder changes RSVP status from the "manage my rsvp" screen. It fires the mutation immediately on click with no dialog at all. If this surface is left ungated, a token holder can flip to "attending" without ever seeing a payment prompt — the same gap as skipping a sibling caller of a function being fixed.

### Backend choke point

Both member and public RSVP submission paths already funnel through one function: `_apply_rsvp_in_transaction` (`backend/community/_event_rsvps.py:134`). This is the single place a server-side "payment must be confirmed" guard would live if the confirmation needs to be enforced (not just UI-gated) — both `_event_rsvps.py`'s member path and `_public_rsvp_submit.py`'s public/new-person path call into it.

The closest existing pattern for a persisted confirmation timestamp is the join-flow's `sms_consent_at` / `guidelines_consent_at` nullable `DateTimeField`s on `join_form.py` — not wired to RSVP today, but a reasonable shape to mirror for a new `paid_confirmed_at` on `EventRSVP` if the confirmation should be durable/auditable rather than a client-only gate.

## Relevant code

| Area | Location | Role |
|---|---|---|
| Event payment fields | `backend/community/models/event.py:63-66` | `price`, `venmo_link`, `cashapp_link`, `zelle_info` — already exist |
| EventRSVP model | `backend/community/models/event.py:183-212` | No confirmation field today; would need one for a persisted gate |
| Member RSVP schema | `backend/community/_event_schemas.py:228-233` (`RSVPIn`) | `status`, `has_plus_one`, `comment` only — no confirmation field |
| Public RSVP schema | `backend/community/_public_rsvp_submit.py:39-48` (`PublicRsvpIn`) | name/email/phone/status/plus-one/comment/honeypot — no confirmation field |
| Shared RSVP write path | `backend/community/_event_rsvps.py:134` (`_apply_rsvp_in_transaction`) | Choke point both member and public flows go through — where a server-side gate would live |
| Public submit endpoint | `backend/community/_public_rsvp_submit.py:204-277` (`submit_public_rsvp`) | New-person atomic join+RSVP POST |
| Phone-check branch point | `backend/community/_public_rsvp_submit.py:180-201` (`check_public_rsvp_phone`) | Where member/non_member/new is decided, matching the issue's three flows |
| Consent-timestamp precedent | `backend/community/models/join_form.py:73,77` | `sms_consent_at`, `guidelines_consent_at` — pattern to mirror for `paid_confirmed_at` |
| Cost display (member/token) | `frontend/src/screens/events/EventMemberSection.tsx:173-202` (`CostSection`) | Already renders price + payment links for signed-in/token viewers |
| Payment link formatting | `frontend/src/utils/paymentHandle.ts` | Normalizes Venmo/CashApp handles to URLs |
| Member/token RSVP flow | `frontend/src/screens/events/RsvpSection.tsx`, `RsvpBox.tsx` | Single dialog, single immediate submit — insertion point for flow 1 |
| New-person RSVP flow | `frontend/src/screens/events/PublicRsvpForm.tsx:129-271` (`renderStep`) | Bespoke step machine — insertion point for flow 3 |
| Not-signed-in redirect | `frontend/src/screens/events/PublicRsvpForm.tsx:165-168` | Sends to `/login`, rejoins flow 1 post-login — no separate step needed |
| Token-holder quick-edit (uncovered by issue text) | `frontend/src/screens/events/PublicRsvpCard.tsx:38-71` | Fires mutation immediately on status click, no dialog — must be gated too or it's a bypass |
| Event host form (cost fields) | `frontend/src/screens/events/form/EventFormLinksAndCost.tsx:47-89` | Already lets hosts set price/payment links |

## Options

**A. Client-only confirmation gate (no backend change).**
Add a shared `PaymentConfirmStep` component (reads `event.price`/`venmoLink`/`cashappLink`/`zelleInfo`, shows the pay link + "did you pay? yes" button) and wire it into `RsvpBox.tsx` (covers signed-in member + token via `RsvpSection`), `PublicRsvpForm.tsx`'s step machine (new person), and `PublicRsvpCard.tsx` (token quick-edit). Gate only fires when the event has cost info and the target status is "attending"/going.
- Trade-off: purely a UX nudge — nothing stops a client that skips the step (modified request, API called directly) from RSVPing unpaid. Smallest diff; matches how the rest of the app already treats consent-style steps (no server enforcement exists for anything comparable today either).

**B. Server-enforced gate.**
Everything in A, plus a `paid_confirmed_at` (nullable `DateTimeField`, mirroring the join-form consent pattern) on `EventRSVP`, added to `RSVPIn`/`PublicRsvpIn`, and enforced inside `_apply_rsvp_in_transaction` when the event has cost info and status is going. Requires a migration.
- Trade-off: real enforcement and an auditable record of confirmation, at the cost of a schema change and touching the shared write path used by every RSVP flow (including host-side and admin RSVP edits, which would also need to bypass or satisfy the new gate).

## Recommendation

Option A (client-only gate) for a first pass, with the shared `PaymentConfirmStep` component as the one piece of genuinely reusable UI worth extracting — the alternative is writing the same gate twice (once in `RsvpBox`, once in `PublicRsvpForm`) plus a third time in `PublicRsvpCard`. This matches the issue's literal ask (a confirmation prompt in the flow) without a schema/migration change, and it's consistent with the fact that no other consent-style step in this codebase is server-enforced today. If payment fraud/no-shows become a real problem later, option B's persisted field can be layered on top of the same UI without redoing the step components.

Regardless of option chosen, the fix must cover **all four** mutation surfaces (`RsvpBox`, `PublicRsvpForm`, `PublicRsvpCard`, and the post-login rejoin into `RsvpBox`) — gating only the new-person form and leaving the token quick-edit card ungated would reproduce the issue for a subset of users.

## Open questions

- **Which RSVP statuses require confirmation?** Presumably only "attending"/going (not "maybe" or "can't go"), but the issue doesn't say explicitly. Assumed here; needs confirmation before implementation.
- **Should the gate apply retroactively to status changes**, e.g. a token holder in `PublicRsvpCard` flipping from "maybe" to "going" — or only to a fresh RSVP? The issue's flows all describe first-time RSVPing.
- **What counts as "the event has a cost"?** `price` is free text ("free", "sliding scale", "$10" — see `formatPrice()` in `EventMemberSection.tsx:207`), not a number, so "non-empty and not literally 'free'" is a heuristic, not a clean boolean. Could alternatively gate on "any of price/venmo/cashapp/zelle is set," which is simpler but would also gate events where price is explicitly "free" but a payment link is set for some other reason (e.g. optional donations).
- **Should already-RSVP'd members be retroactively prompted** (e.g. next time they view the event) or only newly-created/changed RSVPs?
- **Server enforcement (option B) vs. UI-only (option A)** — recommendation above is UI-only; confirm this is acceptable given there's no precedent either way in this codebase for enforcing a consent-style step server-side.
- **Does an event host/admin RSVPing a guest manually** (if that capability exists) need to go through the same gate, or is it exempt?
