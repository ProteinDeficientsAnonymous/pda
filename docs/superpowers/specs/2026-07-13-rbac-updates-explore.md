# Explore: RBAC updates (#541) — Findings

**Date:** 2026-07-13
**Issue:** https://github.com/ProteinDeficientsAnonymous/pda/issues/541
**Branch / PR:** `auto-541-explore-rbac-cedar-granularity` (draft PR linked on push)

## The ask

Issue #541 has two parts:

1. **Evaluate Amazon Cedar** as a possible overhaul of PDA's RBAC — "see if we can
   overhaul our current rbac and utilize this instead."
2. **Regardless of Cedar, add `.view`/`.edit` granularity** — split a single
   permission into "can view this page" vs "can edit it," so a role can be granted
   read access to an admin surface without also granting write access.

This is an investigation (the `explore` label). No application code is changed here;
the deliverable is this findings spec + recommendation.

## What we found

### PDA's RBAC today is a small, flat, static role→permission-set model

- **Source of truth:** a single 13-entry `PermissionKey` Django `TextChoices` enum
  (`backend/users/permissions.py:4-17`). Every key is a flat verb-prefixed string
  (`manage_users`, `edit_faq`, `approve_join_requests`, …). **No key uses a dotted
  `resource.view` / `resource.edit` form.**
- **Storage:** `Role.permissions` is a plain `JSONField(default=list)` — a flat JSON
  array of key strings (`backend/users/roles.py:20`). It is **not** an M2M to a
  permission table and has **no DB-level constraint** tying values to `PermissionKey`;
  validity is enforced only in the API layer (`backend/users/schemas.py:14-28`).
- **Assignment:** users get permissions transitively through a `User.roles` M2M
  (`backend/users/models.py:87`).
- **Effective permissions:** `Role.effective_permissions`
  (`backend/users/roles.py:31-38`) returns the stored list — except the default
  `admin` role, which wildcard-expands to `list(PermissionKey.values)` (all keys)
  regardless of its stored contents. `User.has_permission(key)`
  (`backend/users/models.py:143-155`) is a simple OR-union: true if any of the user's
  roles grants the key. There is **no `is_superuser` bypass** in `has_permission` —
  superusers get full access indirectly because a `post_save` signal auto-assigns them
  the `admin` role.

Because keys are opaque strings in a JSON array, **introducing dotted `page.view` /
`page.edit` keys needs no schema migration** — only enum additions, mirror updates, a
data migration to rewrite existing role arrays, and per-call-site enforcement changes.

### Enforcement is hand-written inline checks at ~55 call sites — no decorator

Every gated endpoint calls `request.auth.has_permission(PermissionKey.X)` inline and,
on failure, `raise_validation(Code.Perm.DENIED, status_code=403, …)`
(`backend/community/_validation.py:165-166,242-263`). There is **no permission
decorator or Ninja auth class** — the shared `gated_jwt` auth
(`backend/config/auth.py:42-80`) enforces account state, not permissions. So a
`.view`/`.edit` split is a per-site edit at every gated endpoint, not a one-line
central change.

### Several endpoints already gate VIEW (GET) and EDIT (write) with ONE key — the split candidates

These are where the issue's granularity ask actually bites — a single key currently
guards both reading an admin surface and mutating it:

| Permission | Shared GET (view) | Shared writes (edit) |
|---|---|---|
| `MANAGE_SURVEYS` | `list_surveys_admin` (`_surveys.py:48`), `get_survey_admin` (`_surveys.py:130`), `list_survey_responses` (`_surveys.py:394`) | POST/PATCH/DELETE/PUT across `_surveys.py` |
| `MANAGE_DOCUMENTS` | `list_folders` (`_docs.py:143`), `get_document` (`_docs_documents.py:108`) | all folder/document writes |
| `MANAGE_USERS` | `list_users` (`_management.py:249`) | update/delete/roles/bulk (`_management.py`) |
| `APPROVE_JOIN_REQUESTS` | `list_join_requests` (`_join_requests.py:114`) | status/unreject/resend writes |
| `MANAGE_EVENTS` | `attendance_report` (`_attendance_report.py:25`), `list_event_flags` (`_event_flags.py:104`) | flag-review PATCH, event mutations |
| `MANAGE_ROLES` | `list_roles` (`_roles.py:24`, also accepts `MANAGE_USERS`) | role create/update/delete |

These `manage_*` keys are the prime split targets. On the frontend, `/docs` is
additionally **route-guarded** by `ManageDocuments` (`frontend/src/router/routes.tsx`),
so today a user must have the manage perm even to *view* the docs library — a split
would let view-only roles in.

### Content pages already have a de-facto view/edit split — via `auth=None`, not a paired key

`edit_guidelines` / `edit_faq` / `edit_homepage` / `edit_join_questions` gate only the
PATCH; the corresponding GET endpoints are **public** (`auth=None`) and the pages are
openly viewable (`_guidelines.py`, `_home.py`, `_join_form.py`). The frontend expresses
this with a reusable `EditableHtmlBlock` (`canEdit` prop) and `canManage` booleans
threaded from a single permission. So for these pages "view = everyone, edit = perm"
already holds — they do **not** need a new `.view` key; only the `manage_*` surfaces do.

### The frontend mirrors permissions in THREE hand-maintained places

A `.view`/`.edit` split multiplies the sync burden across:

1. `backend/users/permissions.py` — the enum (source of truth).
2. `frontend/src/models/permissions.ts:3-17` — the `Permission` mirror (a comment at
   `:1-2` explicitly says "keep in sync").
3. `frontend/src/screens/admin/RoleFormDialog.tsx:21-35` — the hand-maintained
   `PERMISSION_LABELS` map that renders the role editor's checkbox grid. **A key
   missing here is silently ungrantable in the UI.**

Route access is gated by `RequirePermission` (`frontend/src/auth/guards.tsx:125-138`)
and admin-hub tiles self-filter by `hasPermission` — all single-key, no view/edit
notion. The role editor is a **flat, ungrouped checkbox grid** (one peer checkbox per
key, no resource grouping) — splitting keys without grouping them would roughly double
the flat list and hurt usability.

### A dotted-pair convention is already documented (but unused in PDA)

The repo's `/audit-permissions` skill documents `resource.view` / `resource.edit` as the
**preferred pattern for new permission keys** — it groups related capabilities and makes
privilege escalation visible ("`.edit` without `.view` is an obvious mistake"). PDA has
**zero dotted keys today**, so `member_list.view`/`.edit` in that skill is an *example of
the convention*, not an existing PDA key. This issue is the natural first application of
that documented convention.

### Cedar

No Cedar usage or dependency exists anywhere in the backend (`grep -rni cedar backend/`
is empty). See the evaluation below.

## Relevant code

| Area | Location | Role |
|---|---|---|
| Permission source of truth | `backend/users/permissions.py:4-17` | 13 flat `PermissionKey` keys |
| Role storage | `backend/users/roles.py:20` | `permissions = JSONField(default=list)` |
| Effective perms (admin wildcard) | `backend/users/roles.py:31-38` | expands admin role to all keys |
| Per-user check | `backend/users/models.py:143-155` | `has_permission` OR-union across roles |
| Key validation | `backend/users/schemas.py:14-28` | rejects keys not in `PermissionKey.values` |
| 403 helper | `backend/community/_validation.py:165-166,242-263` | `Code.Perm.DENIED` → 403 |
| Data-migration precedent | `backend/users/migrations/0010_rename_manage_guidelines.py`, `0021_drop_edit_welcome_message_perm.py` | rewrite role JSON arrays on key rename/remove |
| Seed roles | `backend/users/migrations/0003_seed_default_roles.py` | `member` (no perms), `admin` (wildcard) |
| Frontend mirror | `frontend/src/models/permissions.ts:3-17` | `Permission` const object |
| Role editor labels | `frontend/src/screens/admin/RoleFormDialog.tsx:21-35` | hand-maintained `PERMISSION_LABELS` |
| Route guard | `frontend/src/auth/guards.tsx:125-138` | `RequirePermission` single-key gate |
| View/edit UI primitive | `frontend/src/components/EditableHtmlBlock.tsx:17` | `canEdit` prop (existing view/edit UX) |

## Options

### Part 1 — Cedar

- **A. Adopt Cedar via AWS Verified Permissions (managed service).** Cedar's supported,
  low-effort path. But PDA deploys on **Railway, not AWS** — this adds an AWS account
  dependency plus a network authorization round-trip on every check (latency +
  availability coupling) and per-request cost, to replace what is currently in-memory
  set membership. Poor fit.
- **B. Adopt Cedar self-hosted (Rust engine in-process).** Stays off AWS and is fast
  (in-process), but Cedar's engine is Rust with **no first-party Python SDK**; the
  practical binding is the community `cedarpy` PyO3 wrapper — a single-maintainer
  dependency on a security-critical path — plus native-wheel build complexity in the
  Railway image. It also makes the **frontend mirror worse**: Cedar decisions are
  contextual (per-resource/attribute), so a static string mirror no longer suffices —
  you'd need client-side policy eval (WASM + synced entity store) or per-resource
  "can I?" API calls.
- **C. Do not adopt Cedar; keep the flat model.** Cedar's value is ABAC / per-resource /
  hierarchical / analyzable policy-as-code. PDA has 13 flat keys, a few static roles, and
  union semantics — no requirement Cedar uniquely satisfies today.

### Part 2 — `.view`/`.edit` granularity (independent of Cedar; does not require it)

- **A. Split every `manage_*` key into `resource.view` + `resource.edit` pairs.** Full
  realization of the ask. Largest surface: enum + 3 frontend mirrors + a data migration
  + choosing view-vs-edit at each of the ~6 shared-key GET sites and their writes, plus
  updating route guards (e.g. `/docs`) and grouping the role-editor UI so it doesn't
  become an unreadable flat list.
- **B. Split only where a view-only audience is real** (start with `manage_surveys` and
  `manage_documents` — the clearest "let people read the admin surface without editing"
  cases), using the dotted convention, and leave `edit_*` content-page keys alone (they
  already have open view + gated edit). Incremental; each split is one focused PR
  under the 400-line limit.
- **C. Introduce the dotted `resource.view`/`resource.edit` convention + a small
  `require_permission(view=..., edit=...)` enforcement helper first**, then migrate
  surfaces onto it one at a time. Pays down the "55 inline checks" smell noted by the
  audit and gives one seam to evolve behind.

## Recommendation

**Part 1 — Cedar: do not adopt (Option C).** For a small community platform with a
handful of static roles and flat permission keys, Cedar is overkill and a poor
ecosystem fit: no first-party Python SDK, and the supported path pulls in an AWS
dependency that conflicts with PDA's Railway deployment. It would also make the frontend
permission-sync story worse, not better, because contextual decisions can't be mirrored
by a static string list. Revisit Cedar **only if** a genuine ABAC requirement appears
(e.g. "club leaders may edit only their own club's events," regional approvers) *across
enough resources* that hand-rolled Python conditions become unmaintainable — and even
then evaluate a lightweight in-process engine (OPA/oso or a then-vetted Cedar binding)
before defaulting to AWS. The early smell to watch: the existing per-resource checks
`_enforce_type_tag_permission` (`backend/community/_events.py`) and
`_has_finalize_permission` (`backend/community/_survey_helpers.py`).

**Part 2 — `.view`/`.edit` granularity: implement in the existing flat model, phased
(Option B, framed by Option C).** This is a small, well-understood extension and does
**not** need Cedar. Concretely, phased to stay under the 400-line-per-PR limit:

1. **PR 1 — convention + helper (foundational).** Add a `require_permission(request, *,
   view=None, edit=None)` (or similar) enforcement helper and adopt the dotted
   `resource.view`/`resource.edit` naming, following the `/audit-permissions` convention.
   No behavior change yet.
2. **PR 2 — first split: surveys.** Introduce `surveys.view` + `surveys.edit`, data-migrate
   existing `manage_surveys` grants to *both* halves (preserving current access), update
   the 3 GET sites to require `.view` and writes to require `.edit`, mirror in
   `permissions.ts` + `PERMISSION_LABELS`, and group the role editor UI by resource so
   the checkbox list stays readable.
3. **PR 3 — second split: documents** (same shape; also relax the `/docs` route guard to
   the `.view` key). Repeat for `manage_users` / `approve_join_requests` / `manage_events`
   only where a view-only audience is genuinely wanted.

Leave the `edit_*` content-page keys (`edit_guidelines`/`edit_faq`/`edit_homepage`/
`edit_join_questions`) as-is — those pages are already publicly viewable with edit-only
gating, so they need no `.view` counterpart.

Migration safety note: when splitting a key, the data migration must grant **both**
`.view` and `.edit` to any role that had the old `manage_*` key, so existing roles keep
their current (view+edit) access — mirroring the `0010`/`0021` rewrite precedents. Do
**not** auto-create a `.edit` without a `.view` (the audit skill flags edit-without-view
as almost certainly an oversight).

## Open questions

1. **Scope of the split — all `manage_*` keys, or only where a view-only audience is
   real?** The recommendation is incremental (surveys + documents first). Confirm which
   surfaces genuinely need a read-only role before splitting the rest — splitting all six
   at once doubles the flat permission list and may not match any real role need.
2. **Backfill semantics on split.** Recommendation: grant existing `manage_*` holders
   **both** `.view` and `.edit` (no access change). Confirm this is desired vs. a
   deliberate downgrade of some roles to view-only.
3. **`/docs` route guard.** Viewing the docs library is currently gated by
   `ManageDocuments`. Splitting implies view-only members could reach `/docs` — is opening
   docs to a `documents.view` role the intended product behavior, or should docs stay
   fully manage-gated?
4. **Role-editor UX.** The editor is a flat ungrouped checkbox grid; doubling keys needs
   resource grouping (and possibly linking `.edit` to auto-imply `.view`) to stay usable.
   Is a UI grouping/redesign in scope for this issue, or a separate follow-up?
5. **Enforcement-helper refactor.** Introducing `require_permission(view=, edit=)` touches
   ~55 inline call sites over time. Do this as the foundational first PR (recommended), or
   keep the inline-check pattern and only add dotted keys?
6. **Cedar live-fact check (low stakes).** The Cedar evaluation could not fetch live docs
   (web tools were unavailable in the sandbox). Recommendation stands regardless, but if
   Cedar is ever reconsidered, verify current `cedarpy` maintenance status and AWS Verified
   Permissions pricing first.
