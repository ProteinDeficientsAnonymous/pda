# RSVP Notes → Comments + Partiful-style RSVP Box — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rework PR #798 so an optional RSVP note routes by status — going/maybe notes become public event comments (host notified); can't-go notes become ephemeral host-only in-app notifications — and restructure the RSVP UI into a Partiful-style confirmation box with an "edit RSVP" flow.

**Architecture:** The note stays a per-request input on `RSVPIn` but is no longer persisted on the `EventRSVP` row. Inside the RSVP write transaction, a going/maybe note creates an `EventComment` (reusing `notify_event_comment`); a can't-go note calls a new `notify_rsvp_declined_note` service that creates host/co-host `Notification` rows and is then discarded. The frontend replaces inline RSVP controls with a modal box (note + +1) shown on any pill tap, and a status line + "edit RSVP" button once the member has responded.

**Tech Stack:** Django + django-ninja (Pydantic schemas), PostgreSQL, pytest; React + TypeScript, TanStack Query, Vitest/RTL, Tailwind.

## Global Constraints

- **Worktree path (all git/commands run here):** `/Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note`. The session shell cwd resets to the skillet repo between commands, so **always use absolute paths**, and for git use `git -C /Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note …` with the **literal path** (a `$VAR` in the command is not expanded by the commit hook and will be misjudged as `main` → blocked).
- **Branch:** `auto-297-rsvp-note` (never commit on `main`).
- **No `Co-Authored-By` needed** — but it is allowed in this repo (pda), unlike skillet. Keep commit messages conventional-commit style (`feat:`, `test:`, `refactor:`, `docs:`).
- **File size:** keep files < 300 lines target, 500 hard max.
- **No nested ternaries** (user rule) — use early returns or extracted components.
- **Note max length:** 300 chars (input); comment `body` DB max is 500 (truncate defensively with `[:500]`).
- **Notification `notification_type` max_length:** 32 (new value `rsvp_declined_note` = 18 chars, fits).
- **Verification:** run `make agent-ci` (or the backend/frontend equivalents) before declaring done; fix all type/lint/test errors.
- **RSVPStatus values:** `ATTENDING="attending"`, `MAYBE="maybe"`, `CANT_GO="cant_go"`, `WAITLISTED="waitlisted"` (from `community/models/choices.py`).

---

## File Structure

**Backend**
- `backend/notifications/models.py` — add `NotificationType.RSVP_DECLINED_NOTE`.
- `backend/notifications/service.py` — add `notify_rsvp_declined_note(event, author, note)`.
- `backend/community/_event_rsvps.py` — route the note to comment/notification inside the RSVP transaction; stop persisting it on the row.
- `backend/community/_event_schemas.py` — remove `RSVPGuestOut.note` and `EventDetailOut.my_rsvp_note`; keep `RSVPIn.note`.
- `backend/community/models/event.py` — remove `EventRSVP.note` field.
- `backend/community/migrations/0062_eventrsvp_note.py` — **delete**.
- `backend/community/_event_helpers.py` — remove note from `_event_out` / guest serialization.
- `backend/openapi_schema.json` — regenerate.
- Tests: `backend/tests/test_rsvp_note.py` (rewrite), `backend/tests/test_rsvp_declined_note.py` (new, notification), plus revert incidental churn in `test_event_helpers.py`.

**Frontend**
- `frontend/src/screens/events/RsvpBox.tsx` — **new** modal (status + note + +1; edit mode hides note).
- `frontend/src/screens/events/RsvpNoteField.tsx` — simplify to a controlled textarea used inside the box.
- `frontend/src/screens/events/RsvpSection.tsx` — pills→box when not RSVP'd; status line + "edit RSVP" when RSVP'd; revert unrelated churn.
- `frontend/src/screens/events/RsvpGuestList.tsx` — revert to `origin/main`.
- `frontend/src/api/rsvp.ts` — keep sending `note` (already does); no `myRsvpNote` read.
- `frontend/src/api/eventMapper.ts`, `frontend/src/models/event.ts`, `frontend/src/api/types.gen.ts` — remove `note`/`myRsvpNote`; regenerate `types.gen.ts`.
- `frontend/src/test/fixtures.ts` — remove `note`/`myRsvpNote` fixture fields.
- Tests: `RsvpBox.test.tsx` (new), `RsvpNoteField.test.tsx` (rewrite), revert incidental `.test` churn.

---

## Task 1: Add `RSVP_DECLINED_NOTE` notification type + `notify_rsvp_declined_note` service

**Files:**
- Modify: `backend/notifications/models.py` (`NotificationType` TextChoices)
- Modify: `backend/notifications/service.py` (add function)
- Test: `backend/tests/test_rsvp_declined_note.py` (create)

**Interfaces:**
- Consumes: `Notification`, `NotificationType` (`notifications/models.py`); `_notify_users(user_ids: Iterable[str])` (`notifications/service.py`).
- Produces: `notify_rsvp_declined_note(event: Event, author: User, note: str) -> None` — creates a `Notification(notification_type=RSVP_DECLINED_NOTE, event=event, related_user=author, message=...)` for each host/co-host except `author`; no-op if the recipient set is empty; then `_notify_users(recipient_ids)`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_rsvp_declined_note.py`:

```python
"""Tests for the can't-go RSVP note → host-only notification path (issue #297)."""

import pytest
from community.models import Event
from notifications.models import Notification, NotificationType
from notifications.service import notify_rsvp_declined_note
from users.models import User

from tests.conftest import future_iso


@pytest.mark.django_db
class TestNotifyRsvpDeclinedNote:
    def _event(self, host):
        return Event.objects.create(
            title="Party",
            start_datetime=future_iso(days=10),
            created_by=host,
        )

    def test_notifies_host(self, test_user, db):
        decliner = User.objects.create_user(
            phone_number="+12025550808",
            password="pw",
            display_name="Decliner",
        )
        event = self._event(test_user)
        notify_rsvp_declined_note(event=event, author=decliner, note="out of town, sorry!")
        notifs = Notification.objects.filter(
            recipient=test_user,
            notification_type=NotificationType.RSVP_DECLINED_NOTE,
        )
        assert notifs.count() == 1
        n = notifs.first()
        assert n.event_id == event.id
        assert n.related_user_id == decliner.id
        assert "out of town, sorry!" in n.message

    def test_notifies_cohosts_excludes_author(self, test_user, db):
        cohost = User.objects.create_user(
            phone_number="+12025550809", password="pw", display_name="Cohost"
        )
        event = self._event(test_user)
        event.co_hosts.add(cohost)
        # Author is the host themselves — they should NOT notify themselves.
        notify_rsvp_declined_note(event=event, author=test_user, note="hi")
        assert not Notification.objects.filter(
            recipient=test_user, notification_type=NotificationType.RSVP_DECLINED_NOTE
        ).exists()
        assert Notification.objects.filter(
            recipient=cohost, notification_type=NotificationType.RSVP_DECLINED_NOTE
        ).count() == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note/backend && python -m pytest tests/test_rsvp_declined_note.py -v`
Expected: FAIL — `ImportError: cannot import name 'notify_rsvp_declined_note'` (and `RSVP_DECLINED_NOTE` missing).

- [ ] **Step 3: Add the notification type**

In `backend/notifications/models.py`, inside `class NotificationType(models.TextChoices)`, add after `EVENT_COMMENT`:

```python
    RSVP_DECLINED_NOTE = "rsvp_declined_note", "RSVP Declined Note"
```

- [ ] **Step 4: Add the service function**

In `backend/notifications/service.py`, add (mirroring `notify_event_comment`'s recipient logic):

```python
def notify_rsvp_declined_note(event, author, note: str) -> None:
    """Notify host + co-hosts that someone who can't go left a note.

    Host-only and ephemeral: the note is not stored anywhere else. No-op if
    the only recipient would be the author (e.g. host declining their own event).
    """
    author_id_str = str(author.pk)
    recipient_ids: set[str] = set()
    if event.created_by_id is not None:
        recipient_ids.add(str(event.created_by_id))
    recipient_ids.update(str(u.pk) for u in event.co_hosts.all())
    recipient_ids.discard(author_id_str)
    if not recipient_ids:
        return
    name = author.display_name or author.phone_number
    message = f"{name} can't go: “{note}”"[:255]
    recipient_id_list = sorted(recipient_ids)
    Notification.objects.bulk_create(
        [
            Notification(
                recipient_id=rid,
                notification_type=NotificationType.RSVP_DECLINED_NOTE,
                event=event,
                related_user=author,
                message=message,
            )
            for rid in recipient_id_list
        ]
    )
    _notify_users(recipient_id_list)
```

- [ ] **Step 5: Create the migration for the enum change**

The `notification_type` field is a `CharField` with `choices`; adding a choice needs a migration for `choices` metadata. Run:

`cd /Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note/backend && python manage.py makemigrations notifications`
Expected: creates `notifications/migrations/00XX_alter_notification_notification_type.py`.

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd /Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note/backend && python -m pytest tests/test_rsvp_declined_note.py -v`
Expected: PASS (2 tests).

- [ ] **Step 7: Commit**

```bash
git -C /Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note add backend/notifications/ backend/tests/test_rsvp_declined_note.py
git -C /Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note commit -m "feat(notifications): add rsvp_declined_note host notification"
```

---

## Task 2: Route the RSVP note to comment / declined-notification (backend)

**Files:**
- Modify: `backend/community/_event_rsvps.py` (`_apply_rsvp_in_transaction`, `upsert_rsvp`)
- Test: `backend/tests/test_rsvp_note.py` (rewrite)

**Interfaces:**
- Consumes: `EventComment` (`community.models`), `notify_event_comment` + `notify_rsvp_declined_note` (`notifications.service`), `RSVPStatus`.
- Produces: RSVP POST with a non-empty `note` creates an `EventComment` (going/maybe/waitlisted) or a declined notification (can't-go), inside the RSVP transaction. `EventRSVP` no longer has a `note` attribute after Task 3 — this task must not read/write `rsvp.note`.

**Note on ordering:** This task changes behavior but `EventRSVP.note` still exists until Task 3. Write the routing so it never touches `rsvp.note`. The rewritten tests here assert comment/notification creation, not column persistence, so they pass both before and after Task 3.

- [ ] **Step 1: Rewrite the failing tests**

Replace the body of `backend/tests/test_rsvp_note.py` with:

```python
"""Tests: an optional RSVP note routes to a comment (going/maybe) or a
host-only notification (can't-go), and is not persisted on the RSVP (issue #297)."""

import pytest
from community.models import Event, EventComment, RSVPStatus
from notifications.models import Notification, NotificationType
from ninja_jwt.tokens import RefreshToken
from users.models import User

from tests.conftest import future_iso


@pytest.fixture
def rsvp_event(db, test_user):
    return Event.objects.create(
        title="RSVP Event",
        description="An event with RSVPs enabled",
        start_datetime=future_iso(days=30),
        end_datetime=future_iso(days=30, hours=2),
        location="Community Space",
        rsvp_enabled=True,
        created_by=test_user,
    )


@pytest.fixture
def member(db):
    return User.objects.create_user(
        phone_number="+12025550302", password="pw", display_name="Member"
    )


@pytest.fixture
def member_headers(member):
    refresh = RefreshToken.for_user(member)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


def _rsvp(api_client, headers, event, status, note=None):
    payload = {"status": status}
    if note is not None:
        payload["note"] = note
    return api_client.post(
        f"/api/community/events/{event.id}/rsvp/",
        payload,
        content_type="application/json",
        **headers,
    )


@pytest.mark.django_db
class TestRSVPNoteRouting:
    def test_going_note_creates_comment(self, api_client, member_headers, member, rsvp_event):
        resp = _rsvp(api_client, member_headers, rsvp_event, RSVPStatus.ATTENDING, "bringing snacks")
        assert resp.status_code == 200
        comments = EventComment.objects.filter(event=rsvp_event, author=member)
        assert comments.count() == 1
        assert comments.first().body == "bringing snacks"

    def test_maybe_note_creates_comment(self, api_client, member_headers, member, rsvp_event):
        resp = _rsvp(api_client, member_headers, rsvp_event, RSVPStatus.MAYBE, "might be late")
        assert resp.status_code == 200
        assert EventComment.objects.filter(event=rsvp_event, author=member, body="might be late").count() == 1

    def test_going_note_notifies_host(self, api_client, member_headers, member, rsvp_event, test_user):
        _rsvp(api_client, member_headers, rsvp_event, RSVPStatus.ATTENDING, "yo")
        assert Notification.objects.filter(
            recipient=test_user, notification_type=NotificationType.EVENT_COMMENT
        ).count() == 1

    def test_cant_go_note_creates_no_comment_but_notifies_host(
        self, api_client, member_headers, member, rsvp_event, test_user
    ):
        resp = _rsvp(api_client, member_headers, rsvp_event, RSVPStatus.CANT_GO, "out of town")
        assert resp.status_code == 200
        assert not EventComment.objects.filter(event=rsvp_event, author=member).exists()
        notifs = Notification.objects.filter(
            recipient=test_user, notification_type=NotificationType.RSVP_DECLINED_NOTE
        )
        assert notifs.count() == 1
        assert "out of town" in notifs.first().message

    def test_no_note_creates_nothing(self, api_client, member_headers, member, rsvp_event):
        resp = _rsvp(api_client, member_headers, rsvp_event, RSVPStatus.ATTENDING)
        assert resp.status_code == 200
        assert not EventComment.objects.filter(event=rsvp_event, author=member).exists()
        assert not Notification.objects.filter(
            notification_type=NotificationType.RSVP_DECLINED_NOTE
        ).exists()

    def test_empty_note_creates_nothing(self, api_client, member_headers, member, rsvp_event):
        resp = _rsvp(api_client, member_headers, rsvp_event, RSVPStatus.ATTENDING, "   ")
        assert resp.status_code == 200
        assert not EventComment.objects.filter(event=rsvp_event, author=member).exists()

    def test_status_only_edit_creates_no_new_comment(
        self, api_client, member_headers, member, rsvp_event
    ):
        _rsvp(api_client, member_headers, rsvp_event, RSVPStatus.ATTENDING, "first note")
        assert EventComment.objects.filter(event=rsvp_event, author=member).count() == 1
        # Re-RSVP with no note key (an edit) — must not post another comment.
        _rsvp(api_client, member_headers, rsvp_event, RSVPStatus.MAYBE)
        assert EventComment.objects.filter(event=rsvp_event, author=member).count() == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note/backend && python -m pytest tests/test_rsvp_note.py -v`
Expected: FAIL — no comments/notifications created yet (the note is currently written to the row, not routed).

- [ ] **Step 3: Add note routing in the RSVP transaction**

In `backend/community/_event_rsvps.py`:

1. Add imports at the top with the other `community.models` / service imports:

```python
from community.models import Event, EventComment, EventRSVP, RSVPStatus
from notifications.service import notify_event_comment, notify_rsvp_declined_note
```

2. In `_apply_rsvp_in_transaction`, **remove** the block that writes `note` into `defaults`:

```python
    # DELETE these lines:
    # if note is not None:
    #     defaults["note"] = note.strip()
```

so `defaults` is only `{"status": final_status, "has_plus_one": final_plus_one}`.

3. After the `update_or_create(...)` call and before computing `spot_freed`, add note routing keyed off `final_status`:

```python
    cleaned_note = (note or "").strip()
    if cleaned_note:
        if final_status == RSVPStatus.CANT_GO:
            notify_rsvp_declined_note(event=event, author=user, note=cleaned_note)
        else:
            comment = EventComment.objects.create(
                event=event, author=user, body=cleaned_note[:500]
            )
            notify_event_comment(comment)
```

(Recall `final_status` may be `WAITLISTED` when a going RSVP hits capacity; that falls into the `else` branch and posts a public comment, per the spec's resolved-status routing decision.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note/backend && python -m pytest tests/test_rsvp_note.py -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git -C /Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note add backend/community/_event_rsvps.py backend/tests/test_rsvp_note.py
git -C /Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note commit -m "feat(rsvp): route RSVP note to comment (going/maybe) or host notification (cant-go)"
```

---

## Task 3: Drop the `EventRSVP.note` column, migration, and schema fields (backend)

**Files:**
- Modify: `backend/community/models/event.py` (remove `note` field)
- Delete: `backend/community/migrations/0062_eventrsvp_note.py`
- Modify: `backend/community/_event_schemas.py` (remove `RSVPGuestOut.note`, `EventDetailOut.my_rsvp_note`)
- Modify: `backend/community/_event_helpers.py` (remove note from serialization)
- Modify: `backend/tests/test_event_helpers.py` (revert note assertion added by PR)
- Modify: `backend/openapi_schema.json` (regenerate)

**Interfaces:**
- Consumes: nothing new.
- Produces: `EventRSVP` has no `note` field; `RSVPGuestOut` / `EventDetailOut` have no note fields; OpenAPI schema no longer advertises them.

- [ ] **Step 1: Confirm nothing on the branch depends on migration 0062**

Run: `cd /Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note/backend && grep -rn "0062_eventrsvp_note\|0062" community/migrations/ | grep -v "0062_eventrsvp_note.py:"`
Expected: no downstream migration lists `0062` as a dependency. (If any does, stop and re-point its dependency to `0061_joinrequest_user` before deleting.)

- [ ] **Step 2: Delete the field and migration**

- In `backend/community/models/event.py`, remove the line: `note = models.TextField(blank=True, max_length=300)` from `EventRSVP`.
- Delete the file: `git -C /Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note rm backend/community/migrations/0062_eventrsvp_note.py`

- [ ] **Step 3: Remove note from schemas**

In `backend/community/_event_schemas.py`:
- Remove `note: str = ""` from `class RSVPGuestOut`.
- Remove `my_rsvp_note: str = ""` from the event-detail out schema.
- Keep `RSVPIn.note` (still an accepted input).

- [ ] **Step 4: Remove note from serialization helpers**

In `backend/community/_event_helpers.py`, remove any code that reads `rsvp.note` / sets `note=` on `RSVPGuestOut` or `my_rsvp_note=` on the event out. (Find with: `grep -n "note" backend/community/_event_helpers.py`.)

- [ ] **Step 5: Revert the note assertion in test_event_helpers.py**

In `backend/tests/test_event_helpers.py`, remove the single `note`-related line the PR added (find with `grep -n "note" backend/tests/test_event_helpers.py`).

- [ ] **Step 6: Verify migrations are consistent (no missing migration for the dropped field)**

Run: `cd /Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note/backend && python manage.py makemigrations --check --dry-run community`
Expected: "No changes detected" — because `0062` (which added the field) is deleted, so the model matches migration history at `0061`. If it reports a needed migration, ensure `0062` was actually deleted and the model line removed.

- [ ] **Step 7: Regenerate the OpenAPI schema**

Run the repo's schema export (check `Makefile`/`package.json` for the exact target; commonly):
`cd /Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note/backend && python manage.py export_openapi_schema > openapi_schema.json` *(use the project's actual command if different — grep the Makefile for "openapi")*.
Expected: `note` / `my_rsvp_note` removed from the diff; `RSVPIn.note` retained.

- [ ] **Step 8: Run the backend test suite for events**

Run: `cd /Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note/backend && python -m pytest tests/test_rsvp_note.py tests/test_rsvp_declined_note.py tests/test_event_helpers.py -v`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git -C /Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note add -A backend/
git -C /Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note commit -m "refactor(rsvp): drop persisted EventRSVP.note; note is now comment/notification only"
```

---

## Task 4: Simplify `RsvpNoteField` to a controlled textarea

**Files:**
- Modify: `frontend/src/screens/events/RsvpNoteField.tsx`
- Test: `frontend/src/screens/events/RsvpNoteField.test.tsx` (rewrite)

**Interfaces:**
- Produces: `RsvpNoteField({ value, onChange, disabled }: { value: string; onChange: (v: string) => void; disabled?: boolean })` — a controlled textarea (label, char counter, ≤300). No internal save/edit state, no buttons. Exports `RSVP_NOTE_MAX_LENGTH = 300`.

- [ ] **Step 1: Rewrite the failing test**

Replace `frontend/src/screens/events/RsvpNoteField.test.tsx` with:

```tsx
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { RSVP_NOTE_MAX_LENGTH, RsvpNoteField } from './RsvpNoteField';

describe('RsvpNoteField', () => {
  it('renders the current value', () => {
    render(<RsvpNoteField value="hello" onChange={() => {}} />);
    expect(screen.getByRole('textbox')).toHaveValue('hello');
  });

  it('calls onChange as the user types', () => {
    const onChange = vi.fn();
    render(<RsvpNoteField value="" onChange={onChange} />);
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'hi' } });
    expect(onChange).toHaveBeenCalledWith('hi');
  });

  it('shows remaining characters', () => {
    render(<RsvpNoteField value="ab" onChange={() => {}} />);
    expect(screen.getByText(`${RSVP_NOTE_MAX_LENGTH - 2} characters left`)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note/frontend && npx vitest run src/screens/events/RsvpNoteField.test.tsx`
Expected: FAIL — component still exports the old `note/onSave` API.

- [ ] **Step 3: Rewrite the component**

Replace `frontend/src/screens/events/RsvpNoteField.tsx` with:

```tsx
// Optional note attached to your RSVP (issue #297) — a controlled textarea
// used inside the RSVP box. The note is posted once (as a comment for
// going/maybe, or a host notification for can't-go); it is not editable later.

export const RSVP_NOTE_MAX_LENGTH = 300;

interface Props {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

export function RsvpNoteField({ value, onChange, disabled = false }: Props) {
  const remaining = RSVP_NOTE_MAX_LENGTH - value.length;
  return (
    <div className="flex flex-col gap-2">
      <label htmlFor="rsvp-note" className="text-foreground text-sm font-medium">
        note (optional)
      </label>
      <textarea
        id="rsvp-note"
        rows={2}
        value={value}
        maxLength={RSVP_NOTE_MAX_LENGTH}
        disabled={disabled}
        placeholder="bringing snacks? running late? let people know"
        aria-describedby="rsvp-note-remaining"
        onChange={(e) => {
          onChange(e.target.value);
        }}
        className="focus:border-brand-500 focus:ring-brand-200 border-border-strong bg-surface w-full resize-none rounded-md border px-3 py-2 text-sm transition-colors outline-none focus:ring-2"
      />
      <p id="rsvp-note-remaining" className="text-muted text-xs">
        {remaining} characters left
      </p>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note/frontend && npx vitest run src/screens/events/RsvpNoteField.test.tsx`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git -C /Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note add frontend/src/screens/events/RsvpNoteField.tsx frontend/src/screens/events/RsvpNoteField.test.tsx
git -C /Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note commit -m "refactor(rsvp): make RsvpNoteField a controlled textarea for the RSVP box"
```

---

## Task 5: Build the `RsvpBox` modal (status + note + +1; edit mode hides note)

**Files:**
- Create: `frontend/src/screens/events/RsvpBox.tsx`
- Test: `frontend/src/screens/events/RsvpBox.test.tsx` (create)

**Interfaces:**
- Consumes: `RsvpNoteField` (Task 4); `RsvpStatus` from `@/models/event`; the app's existing modal/dialog primitive (check `@/components/ui/` for `Dialog`/`Modal` — use it; if none, a focus-trapped `div` overlay). `Button` from `@/components/ui/Button`.
- Produces: `RsvpBox({ open, mode, initialStatus, initialHasPlusOne, allowPlusOnes, onConfirm, onClose })` where
  `mode: 'create' | 'edit'`,
  `onConfirm: (args: { status: RsvpInputStatus; note?: string; hasPlusOne: boolean }) => void`.
  In `create` mode it shows the note field and includes `note` in `onConfirm`. In `edit` mode it hides the note field and omits `note`. The +1 toggle shows only when `allowPlusOnes` and the selected status is `attending`.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/screens/events/RsvpBox.test.tsx`:

```tsx
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { RsvpStatus } from '@/models/event';

import { RsvpBox } from './RsvpBox';

const base = {
  open: true,
  initialStatus: RsvpStatus.Attending,
  initialHasPlusOne: false,
  allowPlusOnes: true,
  onClose: () => {},
};

describe('RsvpBox', () => {
  it('shows the note field in create mode', () => {
    render(<RsvpBox {...base} mode="create" onConfirm={() => {}} />);
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });

  it('hides the note field in edit mode', () => {
    render(<RsvpBox {...base} mode="edit" onConfirm={() => {}} />);
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  });

  it('confirms with status, note, and +1 in create mode', () => {
    const onConfirm = vi.fn();
    render(<RsvpBox {...base} mode="create" onConfirm={onConfirm} />);
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'snacks' } });
    fireEvent.click(screen.getByRole('button', { name: /confirm/i }));
    expect(onConfirm).toHaveBeenCalledWith(
      expect.objectContaining({ status: RsvpStatus.Attending, note: 'snacks', hasPlusOne: false }),
    );
  });

  it('omits note in edit mode confirm', () => {
    const onConfirm = vi.fn();
    render(<RsvpBox {...base} mode="edit" onConfirm={onConfirm} />);
    fireEvent.click(screen.getByRole('button', { name: /confirm|save/i }));
    expect(onConfirm).toHaveBeenCalledWith(
      expect.not.objectContaining({ note: expect.anything() }),
    );
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note/frontend && npx vitest run src/screens/events/RsvpBox.test.tsx`
Expected: FAIL — `RsvpBox` does not exist.

- [ ] **Step 3: Discover the modal primitive**

Run: `ls /Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note/frontend/src/components/ui/ | grep -iE "dialog|modal|sheet|popover"`
Use the discovered primitive in the implementation. If none exists, use a simple overlay `div` with `role="dialog"` and an `aria-label`.

- [ ] **Step 4: Implement `RsvpBox`**

Create `frontend/src/screens/events/RsvpBox.tsx`. Use the discovered Dialog primitive (pseudo-shown here with a generic overlay; swap in the real one). Status selection uses simple pills inside the box; the +1 toggle appears only for attending. No nested ternaries — use early returns / small helpers.

```tsx
import { useState } from 'react';

import { Button } from '@/components/ui/Button';
import { RsvpStatus } from '@/models/event';
import { cn } from '@/utils/cn';

import { RsvpNoteField } from './RsvpNoteField';

type RsvpInputStatus = (typeof RsvpStatus)[keyof typeof RsvpStatus];

const STATUS_LABELS: { status: RsvpInputStatus; label: string }[] = [
  { status: RsvpStatus.Attending, label: "i'm going" },
  { status: RsvpStatus.Maybe, label: 'maybe' },
  { status: RsvpStatus.CantGo, label: "can't go" },
];

interface ConfirmArgs {
  status: RsvpInputStatus;
  note?: string;
  hasPlusOne: boolean;
}

interface Props {
  open: boolean;
  mode: 'create' | 'edit';
  initialStatus: RsvpInputStatus;
  initialHasPlusOne: boolean;
  allowPlusOnes: boolean;
  onConfirm: (args: ConfirmArgs) => void;
  onClose: () => void;
}

export function RsvpBox({
  open,
  mode,
  initialStatus,
  initialHasPlusOne,
  allowPlusOnes,
  onConfirm,
  onClose,
}: Props) {
  const [status, setStatus] = useState<RsvpInputStatus>(initialStatus);
  const [note, setNote] = useState('');
  const [hasPlusOne, setHasPlusOne] = useState(initialHasPlusOne);

  if (!open) return null;

  const showNote = mode === 'create';
  const showPlusOne = allowPlusOnes && status === RsvpStatus.Attending;

  function confirm() {
    const trimmed = note.trim();
    const args: ConfirmArgs = { status, hasPlusOne };
    if (showNote && trimmed) args.note = trimmed;
    onConfirm(args);
  }

  return (
    <div
      role="dialog"
      aria-label="RSVP"
      className="bg-surface flex flex-col gap-4 rounded-lg border p-4"
    >
      <div className="flex flex-wrap justify-center gap-2">
        {STATUS_LABELS.map((s) => (
          <button
            key={s.status}
            type="button"
            aria-pressed={status === s.status}
            onClick={() => {
              setStatus(s.status);
            }}
            className={cn(
              'inline-flex h-10 items-center rounded-full px-4 text-sm font-medium',
              status === s.status
                ? 'bg-brand-600 text-brand-on'
                : 'border-border-strong text-foreground-secondary border',
            )}
          >
            {s.label}
          </button>
        ))}
      </div>

      {showPlusOne ? (
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={hasPlusOne}
            onChange={(e) => {
              setHasPlusOne(e.target.checked);
            }}
          />
          bringing a +1
        </label>
      ) : null}

      {showNote ? <RsvpNoteField value={note} onChange={setNote} /> : null}

      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onClose}>
          cancel
        </Button>
        <Button type="button" onClick={confirm}>
          {mode === 'edit' ? 'save' : 'confirm'}
        </Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note/frontend && npx vitest run src/screens/events/RsvpBox.test.tsx`
Expected: PASS (4 tests).

- [ ] **Step 6: Commit**

```bash
git -C /Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note add frontend/src/screens/events/RsvpBox.tsx frontend/src/screens/events/RsvpBox.test.tsx
git -C /Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note commit -m "feat(rsvp): add RsvpBox modal (status + note + plus-one)"
```

---

## Task 6: Wire `RsvpBox` into `RsvpSection`; revert unrelated churn

**Files:**
- Modify: `frontend/src/screens/events/RsvpSection.tsx`
- Modify: `frontend/src/screens/events/RsvpSection.test.tsx`

**Interfaces:**
- Consumes: `RsvpBox` (Task 5), `useSetRsvp` / `useRemoveRsvp` (`@/api/rsvp`), event model fields `myRsvp`, `hasPlusOne` (or wherever the current +1 lives), `allowPlusOnes`.
- Produces: RSVP section that (a) before RSVP shows three pills that open the box in `create` mode; (b) after RSVP shows a status line + "edit RSVP" button that opens the box in `edit` mode. Submitting calls `useSetRsvp().mutateAsync({ eventId, status, hasPlusOne, note })`.

- [ ] **Step 1: Restore the pre-PR baseline, then layer the box on**

First reduce the PR's unrelated churn by diffing against main and keeping only what the box needs:

Run: `git -C /Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note diff origin/main -- frontend/src/screens/events/RsvpSection.tsx`
Review it. The PR replaced `RsvpStatusPicker` with an inline `RsvpPill` and removed `SpotsLeft`/`WaitlistView` — revert those back to the main version *except* where the box flow replaces them. The waitlist view and spots-left indicator from main should be preserved.

- [ ] **Step 2: Write/adjust the failing test**

In `frontend/src/screens/events/RsvpSection.test.tsx`, add:

```tsx
it('opens the RSVP box when a pill is tapped (not yet RSVP’d)', async () => {
  // render RsvpSection with an event where myRsvp is null
  // fireEvent.click the "i'm going" pill
  // expect a dialog with role="dialog" name /RSVP/ to appear
});

it('shows an edit RSVP button once the member has responded', () => {
  // render with myRsvp = attending
  // expect no status pills, expect a button /edit RSVP/i
});
```

Fill these in against the actual `RsvpSection` props/fixtures (mirror the existing tests in the file for render setup).

- [ ] **Step 3: Run test to verify it fails**

Run: `cd /Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note/frontend && npx vitest run src/screens/events/RsvpSection.test.tsx`
Expected: FAIL.

- [ ] **Step 4: Implement the section**

Rework `RsvpSection` so:
- When `myRsvp` is null/none: render the three status pills; tapping one sets `boxMode='create'`, `boxStatus=<tapped>`, opens `RsvpBox`.
- When `myRsvp` is set (attending/maybe/cant_go): render a status line ("you're going" / "you're a maybe" / "you can't go") + an "edit RSVP" `Button` that opens `RsvpBox` in `edit` mode with `initialStatus=myRsvp`.
- `onConfirm` from the box calls `setRsvp.mutateAsync({ eventId: event.id, status, hasPlusOne, note })` (note only present in create mode).
- Keep the waitlist handling (`WaitlistView` / leaveWaitlist) and `SpotsLeft` from the main baseline.
- No nested ternaries — extract a `statusLine(myRsvp)` helper or small components.

- [ ] **Step 5: Run test + typecheck**

Run: `cd /Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note/frontend && npx vitest run src/screens/events/RsvpSection.test.tsx && npx tsc --noEmit`
Expected: PASS + no type errors.

- [ ] **Step 6: Commit**

```bash
git -C /Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note add frontend/src/screens/events/RsvpSection.tsx frontend/src/screens/events/RsvpSection.test.tsx
git -C /Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note commit -m "feat(rsvp): Partiful-style RSVP box + edit-RSVP flow in RsvpSection"
```

---

## Task 7: Revert `RsvpGuestList` + drop `note`/`myRsvpNote` from mapping/types/fixtures

**Files:**
- Modify: `frontend/src/screens/events/RsvpGuestList.tsx` (revert to `origin/main`)
- Modify: `frontend/src/api/eventMapper.ts`, `frontend/src/models/event.ts`, `frontend/src/api/types.gen.ts`, `frontend/src/test/fixtures.ts`
- Modify: incidental `.test.tsx` files the PR touched only to add `note`

**Interfaces:**
- Produces: no `note` on the guest model, no `myRsvpNote` on the event model; `rsvp.ts` still sends `note` in the write payload.

- [ ] **Step 1: Revert RsvpGuestList to main**

Run: `git -C /Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note checkout origin/main -- frontend/src/screens/events/RsvpGuestList.tsx`
(This is restoring a file to a committed state, not discarding uncommitted user work — it reverts the PR's own change.)

- [ ] **Step 2: Remove note/myRsvpNote from model + mapper**

- In `frontend/src/models/event.ts`: remove the `note` field from the guest type and `myRsvpNote` from the event type.
- In `frontend/src/api/eventMapper.ts`: remove the mapping lines that read `note` / `my_rsvp_note`.
- In `frontend/src/api/types.gen.ts`: regenerate from the backend OpenAPI schema (Task 3) rather than hand-editing. Run the repo's codegen (grep `package.json` scripts for `openapi`/`generate`). If codegen isn't wired, remove the `note` / `my_rsvp_note` properties by hand to match the new schema.
- Keep `note` in `rsvp.ts`'s `SetRsvpArgs` and POST body (it's still sent).

- [ ] **Step 3: Fix fixtures + incidental test churn**

- In `frontend/src/test/fixtures.ts`: remove the `note` / `myRsvpNote` fixture fields the PR added.
- For each incidental test the PR modified only to add `note` (`AgendaList.test.tsx`, `CalendarViews.a11y.test.tsx`, `CohostInviteBanner.test.tsx`, `EventAdminActions.test.tsx`, `EventAttendancePanel.test.tsx`, `EventDetailScreen.test.tsx`, `EventMemberSection.test.tsx`, `eventWrites.test.ts`, `event.test.ts`): remove the added `note`/`myRsvpNote` lines. Find with:
  `git -C /Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note diff origin/main -- 'frontend/**/*.test.*' | grep -n "note"`

- [ ] **Step 4: Typecheck + run the affected tests**

Run: `cd /Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note/frontend && npx tsc --noEmit && npx vitest run src/screens/events src/api src/models`
Expected: no type errors; PASS.

- [ ] **Step 5: Commit**

```bash
git -C /Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note add -A frontend/
git -C /Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note commit -m "refactor(rsvp): revert guest-list note display and drop note/myRsvpNote from model/types"
```

---

## Task 8: Full verification + PR body update

**Files:**
- None (verification), then update PR #798 description.

- [ ] **Step 1: Run the full CI target**

Run: `cd /Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note && make agent-ci`
Expected: PASS (backend pytest, frontend vitest, typecheck, lint). Fix any failures before proceeding.

- [ ] **Step 2: Confirm no stray `note` persistence remains**

Run: `cd /Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note && grep -rn "my_rsvp_note\|myRsvpNote" backend/ frontend/src/ | grep -v "\.test\." || echo "clean"`
Expected: `clean` (no source references to the removed fields).

- [ ] **Step 3: Push the branch**

Run: `git -C /Users/leahpeker/development/pda/.claude/worktrees/auto-297-rsvp-note push`
Expected: branch updated on origin.

- [ ] **Step 4: Update the PR description**

Update PR #798's body to describe the new behavior (going/maybe → comment, can't-go → host notification, Partiful-style box, no persisted note column). Use:
`gh pr edit 798 --repo ProteinDeficientsAnonymous/pda --body "<updated body>"`

- [ ] **Step 5: Final commit if any doc/PR-tracking files changed** (else skip).

---

## Self-Review

**Spec coverage:**
- going/maybe → public comment + host notify → Task 2 ✓
- can't-go → ephemeral host-only notification (new type) → Tasks 1, 2 ✓
- one-shot / no edit → Task 2 (frontend doesn't resend) + Task 5 (edit mode hides note) ✓
- auto-waitlist note → public comment → Task 2 Step 3 note ✓
- drop `EventRSVP.note` + migration `0062` + schema fields → Task 3 ✓
- Partiful box (pills open box; note + +1; edit-RSVP after) → Tasks 5, 6 ✓
- revert `RsvpGuestList` + `RsvpSection` churn → Tasks 6, 7 ✓
- mapping/types/fixtures cleanup → Task 7 ✓
- notification in-app only, no email → Task 1 (no email code) ✓
- no host-visible list / toggle for can't-go → not built (correctly absent) ✓

**Placeholder scan:** Task 6 Step 2 leaves the RsvpSection test bodies as guided stubs (they depend on the file's existing render harness, which the implementer must mirror) — this is the one place exact code can't be pre-written without the current test scaffold; flagged explicitly rather than hidden. All other steps have concrete code/commands.

**Type consistency:** `RsvpInputStatus` used consistently in Tasks 5–6; `onConfirm` args `{ status, note?, hasPlusOne }` match between `RsvpBox` (Task 5) and `RsvpSection` (Task 6); `notify_rsvp_declined_note(event, author, note)` signature matches between Tasks 1 and 2; `RsvpNoteField({ value, onChange, disabled })` matches between Tasks 4 and 5.

**Assumptions to verify during execution (not blockers):**
- Exact OpenAPI export command (Task 3 Step 7) and frontend codegen script (Task 7 Step 2) — grep the Makefile/package.json.
- The event model's current +1 field name on the frontend (`hasPlusOne`) and the modal primitive in `components/ui/`.
