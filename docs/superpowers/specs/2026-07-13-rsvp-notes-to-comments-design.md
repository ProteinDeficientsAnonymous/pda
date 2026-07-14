# RSVP notes → comments + Partiful-style RSVP box — Design

**Date:** 2026-07-13
**Branch:** `auto-297-rsvp-note` (PR #798)
**Issue:** #297

## Summary

Rework the "optional RSVP note" feature (PR #798) so that a note attached at RSVP
time flows to the right audience by status, and restructure the RSVP UI into a
Partiful-style confirmation box.

The current PR stores the note as mutable state on the `EventRSVP` row and shows it
in the guest list. This design replaces that with two status-dependent paths and a
new RSVP box UX.

## Behavior

### Note routing by RSVP status

| RSVP status | Note becomes | Audience | Persistence |
|---|---|---|---|
| **going** / **maybe** | a public `EventComment` authored by the member | everyone who can see the event; host notified | persisted (normal comment) |
| **can't go** | an in-app notification to hosts + co-hosts only | hosts/co-hosts only | **ephemeral** — not stored anywhere |

- Notes are **one-shot**: captured only when a member first RSVPs. They cannot be
  edited afterward (a comment, once posted, is an ordinary comment; a can't-go
  notification, once sent, is gone).
- Going/maybe notes post exactly one comment, inside the same transaction as the
  RSVP write, and call `notify_event_comment(comment)` so hosts are pinged like any
  comment.
- Can't-go notes create in-app `Notification` rows for the host + co-hosts with the
  note text, then are discarded. No email. No private column. No host-visible list.

### RSVP box (Partiful-style)

**Before the member has RSVP'd:**
- Three pills: **I'm going**, **maybe**, **can't go**.
- Tapping **any** pill opens the **RSVP box** (a modal/popup), which contains:
  - an optional **note** textarea (≤300 chars), and
  - a **+1** toggle (only meaningful for "going"; shown per existing +1 rules).
- Confirming the box submits status + note + `has_plus_one` together in one request.

**After the member has RSVP'd:**
- The three pills are **removed**. In their place: a short status line ("you're
  going" / "you're a maybe" / "you can't go") and a single **"edit RSVP"** button.
- "edit RSVP" re-opens the box, where the member can change **status** and **+1**.
- The edit box shows **no note field** — notes are one-shot and not editable.

## Backend

### Models

- **Drop** `EventRSVP.note` and migration `0062_eventrsvp_note.py`. The going/maybe
  note lives in `EventComment`; the can't-go note is ephemeral. No note column is
  needed. (Verify nothing on this branch depends on `0062` before deleting; `0061`
  is its parent per exploration.)
- **Add** a `NotificationType.RSVP_DECLINED_NOTE` choice (value
  `"rsvp_declined_note"`, label e.g. "RSVP Declined Note") in
  `backend/notifications/models.py`.

### RSVP endpoint (`backend/community/_event_rsvps.py`)

- Keep `note: str | None` on `RSVPIn` (max 300). It is a per-request input, not
  stored on the RSVP row.
- In `upsert_rsvp` (or `_apply_rsvp_in_transaction`), after the RSVP row is written,
  within the same `transaction.atomic()`:
  - If `note` is non-empty **and** the final status is `ATTENDING` or `MAYBE`:
    ```python
    comment = EventComment.objects.create(event=event, author=user, body=note[:500])
    notify_event_comment(comment)
    ```
  - If `note` is non-empty **and** the final status is `CANT_GO`:
    ```python
    notify_rsvp_declined_note(event=event, author=user, note=note)
    ```
  - Routing keys off the **final resolved status**, not the requested one. A
    "going" RSVP that gets **auto-waitlisted** at capacity resolves to
    `WAITLISTED`, which matches neither branch: for the initial cut, a note on a
    note-carrying RSVP that resolves to `WAITLISTED` posts a **public comment**
    (treated like going/maybe — the member intends to attend). Document this so
    it's a deliberate choice, not an accident.
  - `body[:500]` is a belt-and-suspenders truncation; the input note is already
    capped at 300, and the comment `body` DB max is 500.
- "One-shot" is enforced by the frontend (it only sends `note` on the first RSVP,
  never on an edit). No server-side "already posted" tracking. A crafted client
  resending `note` would post another of *its own* comments — acceptable.

### Notifications (`backend/notifications/service.py`)

- Add `notify_rsvp_declined_note(event, author, note)`: build the host + co-host
  recipient set (same pattern as `notify_event_comment`, excluding the author),
  bulk-create `Notification` rows with `NotificationType.RSVP_DECLINED_NOTE`,
  `related_user=author`, and a message embedding the note (e.g.
  `f"{name} can't go: “{note}”"`), then `_notify_users(recipient_ids)`.

## Frontend

### RSVP box

- **New** `RsvpBox` (modal) component: holds status (preselected from the tapped
  pill), an optional note textarea, and the +1 toggle. On confirm, calls the RSVP
  write mutation with `{ status, note, hasPlusOne }`. In **edit mode** it omits the
  note field and preselects the member's current status/+1.
- **`RsvpNoteField`**: simplify to a plain controlled textarea used *inside* the box
  (no self-contained save/edit loop, no re-POST). Or fold it into `RsvpBox` if that
  reads cleaner.

### `RsvpSection`

- Restructure to the Partiful pattern: pills → box when not RSVP'd; status line +
  "edit RSVP" button → box (edit mode) when already RSVP'd.
- **Revert the incidental churn** the current PR introduced that is unrelated to the
  note: the `RsvpStatusPicker` → inline `RsvpPill` swap and the removed
  `SpotsLeft` / `WaitlistView` / capacity-calc rewrite — *unless* the new box UX
  genuinely requires replacing a helper, in which case keep the minimum needed and
  note it. Do not carry unrelated refactors.

### `RsvpGuestList`

- **Revert entirely** to `origin/main` — remove the note display and its nested
  ternary (which also clears the no-nested-ternaries rule violation).

### Mapping / types

- Remove `note` / `myRsvpNote` from `eventMapper.ts`, `models/event.ts`,
  `types.gen.ts`, and fixtures. Keep only **sending** `note` in the RSVP write
  payload (`rsvp.ts`).
- Regenerate `openapi_schema.json` / `types.gen.ts` from the backend rather than
  hand-editing, so the removed `note` field and any schema drift are consistent.

## Testing

### Backend

- Rewrite `backend/tests/test_rsvp_note.py`:
  - RSVP **going** with a note → one `EventComment` authored by the user with the
    note body; host notified; no `EventRSVP.note` (column gone).
  - RSVP **maybe** with a note → same (comment created).
  - RSVP **can't go** with a note → **no** `EventComment`; a
    `RSVP_DECLINED_NOTE` `Notification` created for host + co-hosts with the text.
  - RSVP with **no note** (any status) → no comment, no declined-note notification.
  - RSVP **going with a note at capacity** (auto-waitlisted) → public comment
    created (per the resolved-status routing decision above).
  - Editing an existing RSVP (no note sent) → no new comment/notification.
- Add/adjust notification tests for `notify_rsvp_declined_note` alongside
  `test_comment_notifications.py`.

### Frontend

- Rewrite `RsvpNoteField.test.tsx` / add `RsvpBox.test.tsx` for: box opens on pill
  tap; confirm submits status+note+plus_one; edit mode hides the note field and
  preselects current status/+1; "edit RSVP" replaces pills after RSVP.
- Revert fixture/test churn that only existed to satisfy the removed `note` fields.

## Migration / cleanup notes

- Delete `0062_eventrsvp_note.py` (branch not merged; no revert migration needed).
- Confirm no downstream migration on the branch references `0062` before deleting.
- Re-run `make agent-ci` (backend + frontend) after changes; the PR body warns the
  diff was recovered from a supervisor worktree and not re-verified against CI.

## Out of scope (YAGNI)

- Editing a posted note. Notes are one-shot by design.
- Persisting or listing can't-go notes (ephemeral notification only, for now).
- Emailing hosts the can't-go note (in-app notification only).
- A host-only "comments vs can't-go notes" toggle (dropped in favor of the
  notification-only approach).
