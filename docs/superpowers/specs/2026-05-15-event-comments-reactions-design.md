# Event comments and emoji reactions — design

**Status:** approved, ready for implementation planning
**Date:** 2026-05-15
**Author:** leahpeker (with Claude)
**Related:** `docs/superpowers/specs/2026-05-15-public-rsvp-official-events-design.md` (the non-member RSVP flow that may, in a future iteration, become the basis for non-member commenting)

## Summary

Add a comments thread to each event detail screen. Logged-in users who have RSVP'd to the event can post plain-text comments (≤500 characters, no editing), reply once to any top-level comment, and react with a fixed set of six emojis (❤️ 😂 🌱 🔥 👍 😭). Authors can delete their own comments. Event creators, co-hosts, and admins with `ManageEvents` can delete others' comments. Deletes are soft-deletes so reply chains stay intact. New replies to a comment trigger an in-app notification to the parent comment's author.

## Scope

### Phase 1 (this design, two PRs)

- `EventComment` and `EventCommentReaction` models with migrations.
- API endpoints to list, post, delete, and react.
- Frontend `EventCommentsCard` rendered inside `EventMemberSection`, below `RsvpSection`, on the event detail screen.
- `NotificationType.COMMENT_REPLY` notification when someone replies to your comment.
- One additional field on `EventOut`: `comment_count` for a future badge.

### Phase 2 (separate spec branch, separate PR, after Phase 1 ships)

- `@mentions` in comments: autocomplete picker against the event's RSVP'd users, persisted mention markers, rendered as clickable references, and a `NotificationType.COMMENT_MENTION` notification.
- The Phase 1 data model intentionally supports this without changes; Phase 2 is purely additive (likely a `CommentMention(comment, user)` join table).

### Out of scope for v1

- Commenting by non-members (waits on the public RSVP flow to figure out session/identity for guests).
- Markdown, autolinking, or rich text in comment bodies.
- Editing comments.
- Notifications to event-wide audiences (e.g. "new comment on an event you RSVP'd to").
- Pagination of the comment list (v1 returns all comments in one response).
- Reporting/flagging individual comments.
- Reactor-list expansion ("who reacted with 🔥?") — Phase 1 ships counts and self-state only.

## Constraints and project conventions

These are derived from existing code, `CLAUDE.md`, and `.claude/rules/*`. The design respects all of them.

- **UUID primary keys** on every new model (`models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)`).
- **`created_at` / `updated_at` / `deleted_at`** as the audit pattern. `updated_at` is included for future-proofing even though Phase 1 does not allow edits.
- **`@rate_limit("10/m")`** on every authed write endpoint per `.claude/rules/rate-limiting-and-input-validation.md`.
- **File size:** target ≤300 LOC per file, hard cap 500 LOC. Comments code is split across multiple files from the start to stay well under the limit.
- **Frontend text is lowercase only**, including dynamic strings via `.toLowerCase()` on `date-fns` output.
- **Pattern to mirror:** `EventPoll` / `PollOption` / `PollVote` — a dedicated module, sub-router (`_polls.py`), schema file (`_event_poll_schemas.py`), and a dedicated FE folder (`screens/events/poll/`) with a TanStack hook (`frontend/src/api/eventPolls.ts`). Comments follow the same shape.
- **Visibility cascade:** every comment read must run through the existing `_enforce_event_read_visibility(event, user)` helper in `_events.py` so `invite_only` events keep their comments private.
- **API client regeneration:** after backend schema changes, `make frontend-types` is run to refresh `frontend/src/api/types.gen.ts`.
- **Pre-merge gate:** `make agent-ci` must pass.

## Eligibility model

Two boolean predicates govern the UI and the API:

- `can_read_comments` — viewer can see the comments list. Equivalent to: the event detail page is visible to them (public event, or member of `members_only`, or invitee of `invite_only`).
- `can_post_comments` — viewer can create comments, replies, and reactions. Equivalent to: logged in **AND** has any `EventRSVP` row for this event (status `yes`, `maybe`, or `no` all count).

Notes:

- Hosts and admins do **not** bypass `can_post_comments`. If they want to comment, they RSVP. They retain a separate moderation power (deleting other people's comments).
- `can_delete` is computed per-comment: `True` if the viewer is the author, the event creator, a co-host, or holds the `ManageEvents` permission.
- Non-member commenting is explicitly deferred until the guest-RSVP flow lands and produces a stable identity (session token, magic link, etc.).

## Data model

All new code in `backend/community/models/comment.py`. The existing `community/models/__init__.py` re-exports the new classes.

### `EventComment`

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDv4 | PK |
| `event` | FK → `Event` | `related_name="comments"`, `on_delete=CASCADE` |
| `author` | FK → `User` | `related_name="event_comments"`, `on_delete=PROTECT` |
| `parent` | FK → `EventComment`, nullable | `related_name="replies"`, `on_delete=CASCADE`. Must be `None` or point to a top-level comment (reply depth = 1). |
| `body` | `TextField(max_length=500)` | Plain text only |
| `created_at` | `auto_now_add=True` | |
| `updated_at` | `auto_now=True` | Future-proofing for edits; Phase 1 never writes to it after create |
| `deleted_at` | `DateTimeField(null=True, blank=True)` | Soft-delete marker |

**Constraints**
- Reply depth = 1 enforced in `clean()` and re-checked at the API layer. No DB-level constraint — the application is the source of truth.
- On create, the API verifies `parent.event_id == event_id` so a reply cannot cross events.

**Indexes**
- `(event, created_at)` — powers the top-level list query, ordered newest-first.
- `(parent, created_at)` — powers reply prefetch, ordered oldest-first.

**Soft-delete semantics**
- When `deleted_at` is set, the API returns `body=""` and `is_deleted=True`.
- Deleting a comment that has replies sets `deleted_at` on the parent only. Replies are untouched and remain visible. (The `on_delete=CASCADE` on the `parent` FK governs hard-deletes, which Phase 1 never performs.)
- Reactions on a deleted comment are hidden in the API response, but the rows are not purged (matches existing soft-delete patterns).
- Deleting an already-deleted comment is idempotent (returns 204 without error).

### `EventCommentReaction`

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDv4 | PK |
| `comment` | FK → `EventComment` | `related_name="reactions"`, `on_delete=CASCADE` |
| `user` | FK → `User` | `on_delete=CASCADE` |
| `emoji` | `CharField(max_length=8, choices=ReactionEmoji.choices)` | Whitelisted |
| `created_at` | `auto_now_add=True` | |

**Constraints**
- `UniqueConstraint(fields=["comment", "user", "emoji"], name="unique_comment_user_emoji_reaction")` — guarantees idempotent toggle semantics.

**Indexes**
- `(comment, emoji)` — powers per-emoji aggregation.

### `ReactionEmoji` choices

`models.TextChoices` enum in the same file:

```
HEART  = "❤️"
JOY    = "😂"
SEEDLING = "🌱"
FIRE   = "🔥"
THUMBS_UP = "👍"
SOB    = "😭"
```

The frontend mirrors this as an `as const` object in `frontend/src/models/eventComment.ts`, matching the existing `EventStatus` pattern. Backend validates `emoji ∈ choices` on every write — invalid emoji returns `422`.

### Notification type

A new value `COMMENT_REPLY` is added to `NotificationType` (closed enum in `backend/notifications/models.py`). Phase 2 adds `COMMENT_MENTION`. Each addition requires a migration; existing rows are unaffected.

## API

All endpoints live in a new router file `backend/community/_event_comments.py`, mounted from `backend/community/api.py` under the events path. Request/response schemas live in `backend/community/_event_comment_schemas.py`.

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/events/{event_id}/comments/` | Optional auth | List top-level comments (newest→oldest) with their replies (oldest→newest) and aggregated reactions. |
| `POST` | `/events/{event_id}/comments/` | Authed + RSVP | Create a top-level comment. Returns the new `EventCommentOut`. |
| `POST` | `/events/{event_id}/comments/{comment_id}/replies/` | Authed + RSVP | Create a reply to `comment_id`. `422` if the target is a reply itself; `404` if the target is missing or soft-deleted. Triggers `notify_comment_reply` (skipped if the replier is the parent's author). |
| `DELETE` | `/events/{event_id}/comments/{comment_id}/` | Authed; author, event creator, co-host, or `ManageEvents` | Soft-delete: sets `deleted_at`, returns 204. Idempotent. |
| `POST` | `/events/{event_id}/comments/{comment_id}/reactions/` | Authed + RSVP | Toggle a reaction. If the `(comment, user, emoji)` row exists, delete it; otherwise create it. Returns the updated `EventCommentOut`. |

**Why a single toggle endpoint** — the unique constraint already guarantees at most one row per `(comment, user, emoji)`, so a single `POST` that flips state matches the user mental model ("tap to toggle") and means the client never needs to track reaction row IDs.

**Validation and errors**
- `403` for missing RSVP on writes, with body `{detail: "rsvp_required"}`.
- `403` for unauthorized delete attempts.
- `404` for missing comments, missing parents, or soft-deleted reply targets.
- `422` for invalid emoji, oversized body, or reply-to-reply attempts.
- `429` for rate-limit (handled by the existing `@rate_limit` decorator).

### Schemas

```python
class CommentReactionSummaryOut(Schema):
    emoji: str
    count: int
    reacted_by_me: bool

class EventCommentReplyOut(Schema):
    id: UUID
    author_id: UUID
    author_display_name: str
    body: str  # "" when is_deleted=True
    is_deleted: bool
    created_at: datetime
    reactions: list[CommentReactionSummaryOut]
    can_delete: bool

class EventCommentOut(EventCommentReplyOut):
    replies: list[EventCommentReplyOut]

class EventCommentListOut(Schema):
    items: list[EventCommentOut]
    can_post: bool
    cannot_post_reason: Literal["login_required", "rsvp_required"] | None

class CommentBodyIn(Schema):
    body: str = Field(..., min_length=1, max_length=500)

class ReactionToggleIn(Schema):
    emoji: str  # validated against ReactionEmoji
```

### Query strategy

The list endpoint executes a single comment query with `select_related("author")` and `prefetch_related("replies__author", "reactions")`. Reactions are aggregated into `CommentReactionSummaryOut` in a Python pass over the prefetched rows. For expected volumes (dozens of comments per event), in-memory aggregation is simpler than a SQL `GROUP BY` join. Revisit if profiling shows a problem.

### `EventOut` change

A single new field, `comment_count: int`, is added to `EventOut` (cheap `.annotate(comment_count=Count("comments", filter=Q(comments__deleted_at__isnull=True)))` in the `_event_out` helper). This powers a future badge on the event card without driving a separate request. The annotation must be included in the event list query too — there is no per-event lazy load.

### Notifications

`backend/notifications/service.py` gains:

```python
def notify_comment_reply(comment: EventComment) -> None:
    """Notify the parent comment's author that someone replied to them."""
```

- No-op if `comment.parent is None` (it's a top-level comment, not a reply).
- No-op if `comment.parent.author_id == comment.author_id` (don't notify yourself).
- Creates `Notification(recipient=comment.parent.author, notification_type=COMMENT_REPLY, event=comment.event, related_user=comment.author, message=...)`.

The reply endpoint calls this helper inside the same transaction as the comment create.

## Frontend

### File layout

```
frontend/src/
  api/eventComments.ts
  models/eventComment.ts
  screens/events/comments/
    EventCommentsCard.tsx
    CommentThread.tsx
    CommentItem.tsx
    ReplyItem.tsx
    CommentComposer.tsx
    ReactionBar.tsx
    DeleteCommentDialog.tsx
    utils.ts
    *.test.tsx (colocated)
```

Every file targets ≤300 LOC. Split further during implementation if any file approaches the cap.

### Integration

A single line is added to `EventMemberSection.tsx`, rendered below `RsvpSection`:

```tsx
<EventCommentsCard eventId={event.id} />
```

`EventCommentsCard` owns its own data fetching, mirroring `EventPollCard`. `EventDetailScreen` and `EventMemberSection` stay small.

### TanStack hooks (`frontend/src/api/eventComments.ts`)

| Hook | Behavior |
|---|---|
| `useEventComments(eventId)` | GET `/events/{eventId}/comments/`. Returns the `EventCommentList`. |
| `usePostComment(eventId)` | POST a top-level comment. Optimistic insert at the top of the list. |
| `usePostReply(eventId, parentId)` | POST a reply. Optimistic insert at the bottom of the parent's `replies`. |
| `useDeleteComment(eventId)` | DELETE a comment. Optimistic flip to `is_deleted=true`, `body=""`. |
| `useToggleReaction(eventId)` | POST `/comments/{id}/reactions/`. Optimistic toggle on the comment's `reactions` array. |

All mutations `invalidateQueries(['eventComments', eventId])` on settle. Mutations that change comment count also invalidate the event detail query so the `comment_count` badge stays fresh. Optimistic updates write the optimistic value in `onMutate`, snapshot the previous state, and roll back in `onError` with a toast.

### UI behavior

- **Empty state (eligible viewer):** "no comments yet" + composer.
- **Empty state (logged out):** prompt to log in (no composer rendered).
- **Empty state (logged in, not RSVP'd):** "rsvp to join the conversation" — composer hidden or shown disabled, depending on visual balance.
- **Composer:** single textarea with a 500-char counter at bottom-right that turns warning color at 450 and red at 500. "post" button disabled while empty, over limit, or submitting. Cmd/Ctrl+Enter submits.
- **Comment row:** avatar (existing user avatar component), display name (lowercase), relative time (`.toLowerCase()`-ed `date-fns` output), body, reaction bar, "reply" link on top-level comments only, "delete" affordance when `can_delete` is true.
- **Reply rows:** indented under their parent, oldest→newest. Visual treatment: small left border + indent. No nested cards.
- **Reaction bar:** six emoji buttons. Each shows its count when ≥1; hidden at 0 for visual quiet. Active state when `reacted_by_me`. Disabled for non-RSVPers with a tooltip explaining why. `aria-pressed` reflects state.
- **Deleted comments:** body replaced with italic "[deleted]" placeholder; replies under a deleted parent stay visible; reaction bar hidden on the deleted row.
- **Tooltips on reactions:** Phase 1 shows count and emoji only. Reactor expansion deferred.

### State ownership

- Server state (comments, reactions): TanStack Query cache. No Zustand store added.
- Composer text: local component state.
- Auth + RSVP status: derived from existing `useAuthStore` plus the event detail query (which already exposes the viewer's RSVP status).

### Accessibility

- Textarea has a visible label or `aria-label`.
- Reaction buttons expose `aria-pressed`.
- Delete confirm uses the existing Dialog primitive (focus-trapped).

### Frontend text rule

All hardcoded strings are written lowercase. Any dynamic string (date formatting, server messages) passes through `.toLowerCase()` before display.

## Testing

### Backend (`backend/tests/community/test_event_comments.py`)

- CRUD happy path: RSVP'd user posts, replies, deletes own; list reflects state.
- Visibility cascade: non-invitee on `invite_only` event gets 404 on list/post.
- RSVP gate: logged-in but no RSVP returns 403 (`rsvp_required`) on post/reply/react; can still GET list when the event is visible to them.
- Reply depth: posting a reply to a reply returns 422; posting a reply to a deleted comment returns 404.
- Reactions: first toggle creates row, second toggle deletes it; reaction summary aggregates counts correctly; `reacted_by_me` reflects the requesting user; invalid emoji returns 422; a single user stacking multiple emojis on one comment works.
- Moderation: event creator deletes another user's comment → 204; random RSVP'd user trying the same → 403; ManageEvents admin → 204.
- Soft-delete behavior: deleted comment returns `body=""`, `is_deleted=True`; replies under it remain visible.
- Notifications: reply to comment X creates a `COMMENT_REPLY` notification for X's author; replying to your own comment creates no notification; top-level comment creates no notification.
- Rate limiting: 11th write in 60s returns 429 (matching existing `@rate_limit` test pattern).

### Frontend (Vitest + React Testing Library)

- `CommentComposer.test.tsx`: disabled when empty, over limit, or not RSVP'd; Cmd+Enter submits; counter color thresholds.
- `CommentItem.test.tsx`: shows delete only when `can_delete`; deleted comments show placeholder; reaction bar disabled for non-RSVPer.
- `ReactionBar.test.tsx`: optimistic toggle flips `aria-pressed` before the mutation resolves; count updates; emoji whitelist enforced.
- `EventCommentsCard.test.tsx`: empty state with composer vs login/rsvp prompt; renders threads with replies in correct order; cache invalidates on post.
- `eventComments.ts` hook tests: optimistic update writes immediately; rollback on error restores the previous snapshot.

### Manual QA before merge

Run `make dev`, open an event, log in as each of: non-RSVP'd member, RSVP'd member, event creator, and `ManageEvents` admin. Verify composer state, reaction toggle, reply, self-delete, moderator delete, and notification arrival. Watch the browser console and network panel for unexpected 4xx/5xx responses.

## Rollout

### PR sequencing

1. **PR 1 — Comments + reactions, no notifications.** Models, migration, API, schemas, FE card + composer + reactions, tests. Ships the visible feature.
2. **PR 2 — Phase 1 finisher: reply notifications.** `NotificationType.COMMENT_REPLY` migration, `notify_comment_reply` helper + wiring, notification tests, FE rendering of the new notification type.
3. **PR 3 — Phase 2: @mentions** (separate spec branch). Mention parsing/storage, autocomplete composer, render layer, `COMMENT_MENTION` notification. Phase 1 data model already accommodates this — Phase 2 is purely additive.

Each PR touches fewer than 10 files and is independently reviewable and revertible.

### Migrations

- `community` app: create `EventComment` and `EventCommentReaction` tables. No data backfill. Reversible.
- `notifications` app: extend `NotificationType` enum with `COMMENT_REPLY`. Existing rows are unaffected (enum widening is safe in Postgres). Reversible (removing the enum value is safe because no rows reference it until Phase 1 PR 2 ships).

### Feature flag

None. This is greenfield surface on a single screen; if something breaks, revert the PR. A flag adds setup overhead without a clear safety benefit for a contained, member-facing feature.

### Deploy path

Normal: push to `main` → Railway staging auto-deploys → manual production deploy via the `deploy-railway.yml` workflow once staging is verified.

## Risks and things to watch

1. **First paginated-list candidate.** v1 returns all comments. At ~100+ comments per event the payload gets chunky and rendering slows. Revisit pagination if any event approaches that volume. Not blocking for v1.
2. **`comment_count` N+1 risk on the event list.** The event list returns many events at once; a per-event count subquery would hurt. The count must be added as a single `annotate(comment_count=Count(...))` in the list query, not a property on the model.
3. **Reply-depth enforcement is application-level.** A direct DB write or a future code path could create a reply-to-reply. Mitigation: `clean()` plus the API check. Add a periodic data integrity check only if this ever becomes a real problem.
4. **Soft-delete vs hard-delete tension.** If a comment is genuinely harmful, soft-delete keeps the row (good for moderation audit, less good for "make it gone"). Phase 1 ships soft-delete only. If a hard-delete need emerges, add an admin-only flag later.
5. **No comment-report flow in v1.** Hosts and admins moderate by direct delete. If reporting becomes necessary, model it after the existing `EventFlag` pattern.
6. **Notification volume on busy events.** Reply notifications are 1:1, so this is bounded. Phase 2's `@mentions` could be noisier — consider per-event mention rate limits when designing Phase 2.

## Open questions for implementation

(None that block writing the plan. The following are choices the implementer can make freely without changing the design.)

- Exact wording of all user-facing strings (must remain lowercase).
- Exact thresholds for the character-counter color states (450/500 is a starting point).
- Whether the composer shows for non-RSVPers as disabled vs hidden — pick whichever reads better in the actual UI.

## Decision log (questions answered during brainstorming)

- **Who can comment?** Logged-in users who have any `EventRSVP` for the event (yes, maybe, or no all count). Non-member commenting deferred until the public-RSVP flow has a stable guest-identity mechanism.
- **Threading depth?** One level (top-level comments + replies, no reply-to-reply).
- **Editing?** No. `updated_at` is included for future-proofing.
- **Deletion?** Author can delete own. Event creator, co-hosts, and `ManageEvents` admins can delete others' (moderation power). Soft-delete with `[deleted]` placeholder.
- **Emoji set?** Fixed whitelist of six: ❤️ 😂 🌱 🔥 👍 😭.
- **Reactable surfaces?** Comments and replies. Not events themselves.
- **One user, multiple emojis on the same comment?** Yes (Slack/Discord behavior). Uniqueness is `(comment, user, emoji)`.
- **Reaction toggle behavior?** Tap to add, tap again to remove.
- **Reaction storage approach?** Single normalized table with server-aggregated counts in the payload. Mirrors `EventPoll`. "Who reacted" deferred (would be a separate endpoint if added later).
- **Comment body?** Plain text, 500 chars. No markdown, no autolinking in v1.
- **Order?** Top-level comments newest→oldest. Replies oldest→newest within each thread.
- **Pagination?** No in v1.
- **Notifications?** Reply-to-your-comment only in Phase 1. `@mentions` in Phase 2. No event-wide "new comment" notification.
- **Placement?** Inside `EventMemberSection`, below `RsvpSection`.
