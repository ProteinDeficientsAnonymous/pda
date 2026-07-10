# Explore: clarify event type vs. visibility taxonomy (they're conflated) (#604) — Findings

**Date:** 2026-07-10
**Issue:** https://github.com/ProteinDeficientsAnonymous/pda/issues/604
**Branch:** `refactor-event-type-visibility-taxonomy` (off `main` @ 12f51dc)

## The ask

An `Event` carries two overlapping axes — `event_type` (official / community) and `visibility` (public / members_only / invite_only). Because **official events must always be public**, the two axes are coupled: the public-RSVP eligibility check (`_load_public_rsvp_event`) requires an event to be **both** `event_type == OFFICIAL` **and** `visibility == PUBLIC`, which is redundant. The issue asks us to decide a clean, orthogonal taxonomy (its straw proposal: `type = official / club / members-only`; `visibility = invite-only vs. not`), plan the migration of existing events, and settle UI copy — before any implementation.

This is a **design/exploration** issue (`explore` + `design` labels). No application code is changed here; this document records the current state, options, a recommendation, and open questions.

## What we found

The reality on the ground differs from the issue's framing in three ways that change the decision:

**1. There is no `club` / `members-only` *type* today.** `event_type` has exactly two values — `official` and `community` (`backend/community/models/choices.py:12`). "Members only" and "invite only" live entirely on the *visibility* axis, not the type axis. The issue's proposed `type = official / club / members-only` would be **new taxonomy**, not a re-slicing of what exists.

**2. `visibility` is a *shared* enum, not event-specific.** `PageVisibility` (`backend/community/models/choices.py:6`) is used by **both** `Event` and `EditablePage` (`backend/community/models/content.py:100`, `backend/community/_pages.py`). Any change to the visibility enum values ripples into the editable-pages feature. A clean event-only redesign should introduce a *separate* event-visibility enum rather than mutating the shared one.

**3. The frontend has already collapsed the two axes into one control.** The event create/edit form presents a single "who can see it" dropdown (`VisibilityChoice`) whose four options — `public`, `members_only`, `invite_only`, `official` — expand to the two backend fields via `visibilityChoiceToFields` (`frontend/src/api/eventWrites.ts:30`). So the user *already* never sets type and visibility independently. The conflation the issue describes is now primarily a **backend model** problem plus **confusing copy**, not a two-knobs-in-the-UI problem.

Given (3), the confusion surfaces as copy, not controls. The `public` and `official` options have near-identical helper text (`frontend/src/screens/events/form/EventFormDetails.tsx:13-28`):
- public → "anyone can see this in the calendar — but only members can see location, links, and rsvp"
- official → "publicly listed as an official pda event — only members can see location, links, and rsvp"

The only functional difference between them today is a badge, a calendar filter label, and the `TAG_OFFICIAL_EVENT` permission gate — not visibility.

### The coupling, precisely

The "official ⇒ public" invariant is enforced in application code (there is **no DB constraint**):

- `_is_invalid_official_visibility(event_type, visibility)` → `event_type == OFFICIAL and visibility != PUBLIC` (`backend/community/_events.py:59`). Called on create (`_events.py:310`) and update (`_events.py:95`); violations raise `event.official_must_be_public` (`backend/community/_validation.py:13`).

Two enforcement sites then *rely* on that invariant and would silently misbehave if it were relaxed:

- **Anonymous list query** shows `PUBLIC OR OFFICIAL` events (`_events.py:151`). The `OFFICIAL` disjunct is redundant *only because* official implies public. If an official event could be non-public, this query would leak it to anonymous users.
- **Read-visibility gate** lets anonymous users see a `members_only` event *iff* it is `official` (`_events.py:246-249`). Same latent assumption — official is treated as a public bypass.

## Relevant code

| Area | Location | Role |
|---|---|---|
| Type enum | `backend/community/models/choices.py:12` | `EventType`: `official`, `community` (no `club`/`members-only`) |
| Visibility enum (**shared**) | `backend/community/models/choices.py:6` | `PageVisibility`: `public`, `members_only`, `invite_only` — used by Event **and** EditablePage |
| Event fields | `backend/community/models/event.py:48-57` | `event_type` (default `community`), `visibility` (default `public`) |
| EditablePage reuse | `backend/community/models/content.py:100`, `_pages.py` | Consumes `PageVisibility` — constrains enum changes |
| Coupling validator | `backend/community/_events.py:59-61` | `official ⇒ public` invariant |
| Coupling error code | `backend/community/_validation.py:13` | `event.official_must_be_public` |
| Create/update enforcement | `backend/community/_events.py:95`, `:310` | Rejects official + non-public (400) |
| Official-tag permission | `backend/community/_events.py:78-92`, `:297-308`; `backend/users/permissions.py:15` | `TAG_OFFICIAL_EVENT` gates official |
| Public-RSVP eligibility | `backend/community/_public_rsvp.py:58-72` | Requires `OFFICIAL` **and** `PUBLIC` (has a `#604` comment already) |
| Anon list filter | `backend/community/_events.py:150-151` | `PUBLIC OR OFFICIAL` — assumes official ⇒ public |
| Invite-only post-filter | `backend/community/_events.py:155-169` | Hides `invite_only` from non-invitees (type-agnostic) |
| Read-visibility gate | `backend/community/_events.py:239-255` | `members_only` hidden from anon **unless official**; invite-only 403 |
| RSVP access gate | `backend/community/_event_rsvps.py:53-68` | Delegates to read-visibility gate |
| Calendar feed | `backend/community/_calendar.py:110-114`, `:141-148` | Invite-only filter (type-agnostic) + ICS reuse of read gate |
| Join-request signal | `backend/community/_join_requests.py:80-82`, `:142-145` | Counts `OFFICIAL` RSVPs as engagement signal (visibility-agnostic) |
| Outbound serialization | `backend/community/_event_helpers.py:386-387` | Both fields always serialized |
| API schemas | `backend/community/_event_schemas.py` | `EventIn`/`EventPatchIn`/`EventListOut`/`EventOut` expose both as plain strings |
| Generated FE types | `frontend/src/api/types.gen.ts` | `event_type` / `visibility` typed as `string` |
| FE constants | `frontend/src/models/event.ts:1-10` | `EventType`, `EventVisibility` mirrors |
| **FE single-control mapping** | `frontend/src/api/eventWrites.ts:30-74` | `VisibilityChoice` ⇄ `{event_type, visibility}` — the UI already merges the axes |
| FE form | `frontend/src/screens/events/form/EventFormDetails.tsx:13-28` | "who can see it" dropdown + helper copy (public/official near-duplicate) |
| FE detail badge | `frontend/src/screens/events/EventDetailScreen.tsx:90-104` | `official` / `invite only` / `members only` badges |
| FE calendar filter | `frontend/src/screens/calendar/AgendaList.tsx:15-18` | `all` / `pda official` / `community` |
| FE colors | `frontend/src/utils/eventColors.ts:1-32` | type×visibility → color matrix |
| FE admin badge | `frontend/src/screens/admin/EventManagementScreen.tsx:153-154` | `official` chip |
| Migrations | `0022_event_type.py`, `0024_event_visibility.py`, `0032_...alter_event_visibility.py` | Field history; `invite_only` added in 0032 (also altered EditablePage) |
| Tests (blast radius) | `backend/tests/` — ~13 files, ~35 refs | Key: `test_event_visibility.py::TestOfficialEventVisibility` (lines 395-466), `test_public_rsvp.py`, `_public_rsvp_helpers.py:47-57` |
| Seed data | `backend/community/management/commands/_seed_data.py:129-173` | 4 events, only `official+public` / `community+public` combos |

## Options

The core question is **what type and visibility should mean, and whether they should be independent axes at all.** Three coherent directions:

### Option A — Keep two axes, decouple cleanly (issue's straw proposal, corrected)

- **type** (who runs it): `official` / `community` — *plus a new `club` value if clubs are a real concept* (see Open Questions).
- **visibility** (who sees/RSVPs): a **new event-specific enum** `EventVisibility = public / members_only / invite_only`, split out from the shared `PageVisibility`.
- Drop the `official ⇒ public` invariant. Rewrite the two dependent sites (`_events.py:151` list filter, `:246-249` read gate) to key off *visibility only*, and public-RSVP eligibility (`_public_rsvp.py`) to `type == OFFICIAL and visibility == PUBLIC` still, but now genuinely orthogonal.
- **Cost:** highest. New enum + data migration + rewrite of 3-4 enforcement sites + ~13 test files + FE mapping. **Risk:** the two decoupled sites are exactly the anonymous-exposure paths — a mistake leaks members-only events publicly.
- **Payoff:** genuinely orthogonal model; official events could in principle be members-only. **But:** does the product actually want a members-only official event? If not, this buys complexity for a state we never use.

### Option B — Collapse to a single axis (visibility only), make "official" a flag

Recognize that `type` and `visibility` aren't really orthogonal in this product: the only type that matters for gating is `official`, and its whole meaning is "public + PDA-run + engagement-signal."

- Keep **visibility** as the one gating axis (`public / members_only / invite_only`), split into an event-specific enum.
- Demote `official` from a *type* to a boolean **`is_official`** flag (still gated by `TAG_OFFICIAL_EVENT`), orthogonal to visibility, with the product rule "official events are public" kept as an explicit, documented invariant rather than an emergent coupling.
- Public-RSVP eligibility becomes `is_official and visibility == PUBLIC` — reads exactly like today but the redundancy is now intentional and named.
- **Cost:** medium. Rename `event_type` → `is_official` (data migration: `official → true`, `community → false`), update join-request signal + badges + filter labels. Enforcement sites keep their current shape.
- **Payoff:** removes the "two enums that must agree" smell; matches how the frontend already thinks (a single choice). Matches the actual product (there is no non-official "type" that changes gating). **Loses** the ability to have a `club` type unless clubs also become a flag/tag.

### Option C — Copy + docs only, defer the model change

The frontend already presents one control; the model coupling is contained and commented. Fix the *actual user-facing confusion* (near-identical `public`/`official` helper text) and document the invariant, without a migration.

- Rewrite the form helper copy so `public` vs `official` reads as a clear distinction (organizer identity + engagement signal, not visibility).
- Add a short model-level docstring / comment stating the `official ⇒ public` invariant and *why* the two axes exist, so the next reader isn't confused.
- **Cost:** low, no migration, no test churn. **Payoff:** resolves the day-to-day confusion. **Doesn't** remove the underlying model smell — a later `club`/public-RSVP-expansion effort still has to do A or B.

## Recommendation

**Adopt Option B (single gating axis + `is_official` flag), but sequence it behind Option C's copy fix.**

Reasoning:
- The frontend has already voted for "one control." The product has exactly one type that affects gating (`official`), and its meaning is inseparable from "public." That's a **flag**, not a co-equal type axis. Option B makes the model match reality and kills the "two enums must agree" invariant at its root, whereas Option A preserves an orthogonality the product doesn't actually use (a members-only official event) at the highest migration cost.
- Splitting an **event-specific visibility enum** out of the shared `PageVisibility` is worth doing under either A or B — the shared enum is a latent coupling to the editable-pages feature and shouldn't constrain event taxonomy.
- Do **Option C first** as a small, shippable PR (copy + invariant docstring): it removes the real user pain immediately and de-risks the model change by making the intended semantics explicit before anyone migrates data.

Concretely, a phased path:
1. **Phase 1 (copy, no migration):** rewrite `public`/`official` helper text; document the invariant at the model. Ship.
2. **Phase 2 (enum split):** introduce `EventVisibility` distinct from `PageVisibility`; data-migrate event rows; leave `event_type` alone. Ship.
3. **Phase 3 (flag):** `event_type` → `is_official` boolean; migrate `official→true`/`community→false`; update join-request signal, badges, filters, public-RSVP check. Ship.

Each phase is independently mergeable and independently revertible, and Phase 1 delivers value even if 2-3 are deferred.

This is a recommendation for discussion, not a mandate — the `club` question (below) could push the decision back toward Option A.

## Open questions

1. **Is `club` a real, needed concept?** The issue proposes `type = official / club / members-only`, but no `club` type exists in code today. If clubs are a genuine product need (distinct from "community"), that argues for keeping a multi-valued **type** axis (Option A) rather than a boolean `is_official` flag (Option B). This is the pivotal product decision and blocks choosing A vs B.
2. **Do we ever want a members-only *official* event?** If yes, the `official ⇒ public` invariant must actually be dropped (Option A). If no (current behavior), Option B's "official is always public" flag is correct. The straw proposal implies decoupling but the product may not need it.
3. **Should the shared `PageVisibility` be split for events specifically?** Recommended yes, but it touches `EditablePage` (`content.py:100`, `_pages.py`). Confirm no page feature depends on events and pages sharing the exact same enum.
4. **Migration of existing production/staging events:** are there any live events in "non-compliant" states (e.g. legacy rows), or is everything `official+public` / `community+public` as the seed data implies? A data audit on staging is needed before writing the migration, since a bad backfill silently changes who can see an event.
5. **Public-RSVP epic dependency (#490 / stages #493-#498):** public RSVP eligibility is one of the tightest consumers of this coupling (`_public_rsvp.py:58-72`). Should this taxonomy change land *before* those stages to avoid reworking them, or are they far enough along that we sequence around them?
6. **Final user-facing copy** for the `public` vs `official` distinction — needs product/design sign-off (all app copy is lowercase per repo convention). Phase 1 can propose wording but the exact strings are a design call.
