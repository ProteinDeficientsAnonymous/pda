# PDA Community Forum — Design Document

*Addressing GH #58 (forum/community board), #57 (event-based group messaging), #110 (WhatsApp replacement)*

## Context

WhatsApp communities have limitations: no search, no threading, no moderation tools, members need WhatsApp. A native forum keeps everything in one place and gives admins more control. This design document explores approaches, recommends an architecture, and lays out a phased implementation roadmap for a community of ~150 members scaling to ~500.

---

## 1. Build vs. Integrate: External Platform Options

Before designing from scratch, GH #110 explicitly asks to evaluate build-vs-integrate tradeoffs. Here are the viable external platforms, evaluated against PDA's stack (Django + Flutter web on Railway, JWT auth, <500 users).

### Self-Hosted Forum Platforms

| Platform | Stack | Flutter Integration | Auth w/ Django | Railway? | Cost |
|----------|-------|-------------------|----------------|----------|------|
| **Discourse** | Ruby/PG/Redis | Iframe only (limited) | DiscourseConnect SSO | Difficult (needs VPS) | Free self-hosted |
| **Flarum** | PHP/MySQL | Iframe | JWT SSO extension | Possible | Free |
| **NodeBB** | Node/MongoDB | Iframe or API | JWT cookie plugin | Possible | Free |

**Verdict**: All work best as standalone apps at a subdomain (e.g., `community.pda.app`), not embedded in Flutter. Discourse is the most mature but hardest to deploy on Railway. NodeBB has the best JWT integration. All require managing a second service + database.

### Chat-as-a-Service (Native Flutter SDKs)

| Platform | Flutter SDK | Auth Integration | Cost (<500 users) |
|----------|------------|-----------------|-------------------|
| **Stream Chat** | Excellent (`stream_chat_flutter`) | Token generation from Django | **Free (Maker Account)** if qualifying; $499/mo otherwise |
| **CometChat** | Good (`cometchat`) | Token exchange from Django | $149/mo (Startup) |
| **Sendbird** | Good | Token-based | $1,199+/mo — too expensive |

**Verdict**: Stream Chat's Maker Account (free for small projects with <$10k revenue, <5 team members, 2,000 MAU) is very attractive if PDA qualifies. Native Flutter widgets = best UX. CometChat is the fallback. Both are SaaS with vendor lock-in.

### Self-Hosted Chat Platforms (Iframe Embed)

| Platform | Embed Method | Auth | Railway? | Cost |
|----------|-------------|------|----------|------|
| **Rocket.Chat** | Iframe with SSO | Iframe-based SSO | Possible (Node+Mongo) | Free (Community Edition) |
| **Matrix/Element** | Dart SDK or iframe | OIDC from Django | Possible (heavy, 2GB+) | Free |
| **Zulip** | No embed (standalone) | OIDC/SAML | Possible | Free |

**Verdict**: Rocket.Chat iframe embed with SSO is the most practical self-hosted chat option. Matrix is powerful but operationally heavy. Both need separate Railway services.

### Real-Time Infrastructure (Build Your Own UI)

| Platform | What It Does | Flutter | Auth | Railway? | Cost |
|----------|-------------|---------|------|----------|------|
| **Centrifugo** | WebSocket pub/sub server | Dart SDK (`centrifuge`) | JWT (native!) | Easy (50MB Go binary) | Free (MIT) |

**Verdict**: Centrifugo is the most architecturally natural fit for PDA. It is NOT a forum/chat app — it is the real-time delivery layer. You build Django models + Flutter UI yourself, Centrifugo handles WebSocket delivery. JWT auth is native. Trivially deploys on Railway. Zero cost. The trade-off: you build everything, but you own everything.

### Integration Strategy Recommendations

| Strategy | Best For | Dev Effort | Ongoing Cost |
|----------|---------|-----------|-------------|
| **A: Stream Chat (Maker)** | Fastest to ship, best UX | Very Low | Free (if qualifying) |
| **B: Build from scratch** | Full control, zero vendor lock-in | High | $0 |
| **C: Build + Centrifugo** | Full control with real-time | High (but simpler RT) | $0 |
| **D: Discourse/NodeBB subdomain** | Full-featured forum, minimal code | Low | $0 + VPS/service cost |
| **E: Rocket.Chat iframe** | Quick chat with self-hosting | Low-Medium | $0 |

---

## 2. Design Alternatives (Architecture Approaches)

### Option A: Threaded Topics (Discourse/Reddit style)

Categories → Topics → Posts/Replies. Good for searchability and long-form discussion. High activation energy to create a thread (title + body + category). Feels formal for a casual community. **WhatsApp replacement score: 5/10.** Loses the immediacy and casual feel.

### Option B: Flat Feed / Timeline (Facebook Group style)

Single stream of posts with inline comments. Lowest friction — post is as simple as typing and submitting. At 150 members this works well; at 500 the feed can get noisy but pinned posts mitigate. **WhatsApp replacement score: 7/10.** Closest to WhatsApp's casual experience.

### Option C: Chat-style Channels (Slack/Discord style)

Real-time channels with message streams. Most faithful WhatsApp recreation. Requires WebSocket infrastructure (Channels + Redis + ASGI migration) — massive technical lift. At 150 members, channels feel empty. **WhatsApp replacement score: 9/10 functional parity, 4/10 feasibility.**

### Option D: Hybrid Feed + Event Discussions (Recommended if building from scratch)

Flat feed (Option B) as the primary experience, with auto-created discussion threads linked to events (#57). Addresses all three issues: casual posting (#58), event-specific conversation (#57), and WhatsApp replacement (#110). Same technical complexity as Option B. Event hosts get automatic moderation over their discussion. **WhatsApp replacement score: 8/10.**

### Option E: External Platform + Custom Event Discussions

Use Stream Chat or Rocket.Chat for general community chat. Build only the event-linked discussion feature (#57) natively. Hybrid approach that gets chat shipped fast while keeping event integration in-house.

### Why Option D (if building from scratch)

1. **Lowest adoption friction** — mirrors how the community uses WhatsApp
2. **Addresses all three GitHub issues** in one system
3. **Fits existing tech stack** — no WebSocket/Redis/ASGI needed
4. **Incremental path to real-time** — start with polling, add Centrifugo later
5. **Community size sweet spot** — enough structure without feeling empty
6. **Zero ongoing costs** — no SaaS fees, no external services

---

## 2. Data Model Design

New Django app: `forum` (separate from `community` to keep models manageable).

### Models

**`Post`** — the core feed unit
| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID PK | |
| `author` | FK(User, SET_NULL, null) | |
| `content` | TextField | Delta JSON (flutter_quill format) |
| `plain_text` | TextField | Denormalized text for search/preview, populated at save |
| `linked_event` | FK(Event, SET_NULL, null, blank) | Bridge to #57 |
| `is_pinned` | BooleanField(False) | Pinned posts float to top |
| `is_locked` | BooleanField(False) | Prevents new comments |
| `status` | CharField(PostStatus) | `published` / `deleted` (soft delete) |
| `created_at` | DateTimeField(auto_now_add) | |
| `updated_at` | DateTimeField(auto_now) | |

Ordering: `["-is_pinned", "-created_at"]`

**`Comment`** — replies to a post
| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID PK | |
| `post` | FK(Post, CASCADE) | |
| `author` | FK(User, SET_NULL, null) | |
| `content` | TextField | Delta JSON |
| `plain_text` | TextField | |
| `parent` | FK(self, CASCADE, null, blank) | One level of nesting max |
| `status` | CharField(CommentStatus) | `published` / `deleted` |
| `created_at` | DateTimeField(auto_now_add) | |
| `updated_at` | DateTimeField(auto_now) | |

Ordering: `["created_at"]` (chronological within a post)

**`Reaction`** — emoji reactions on posts or comments
| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID PK | |
| `user` | FK(User, CASCADE) | |
| `emoji` | CharField(8) | Unicode emoji character |
| `post` | FK(Post, CASCADE, null, blank) | Exactly one of post/comment is non-null |
| `comment` | FK(Comment, CASCADE, null, blank) | DB check constraint enforces this |

unique_together: `(user, emoji, post)` and `(user, emoji, comment)`

**`ReadReceipt`** — tracks last-read position per user per post
| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID PK | |
| `user` | FK(User, CASCADE) | |
| `post` | FK(Post, CASCADE) | |
| `last_read_at` | DateTimeField | Compared against Comment.created_at for unread counts |

unique_together: `(user, post)`

**`Notification`** — in-app notification system
| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID PK | |
| `recipient` | FK(User, CASCADE) | |
| `actor` | FK(User, SET_NULL, null) | |
| `verb` | CharField(50) | `commented`, `reacted`, `mentioned`, `pinned` |
| `post` | FK(Post, CASCADE, null, blank) | |
| `comment` | FK(Comment, CASCADE, null, blank) | |
| `is_read` | BooleanField(False) | |
| `created_at` | DateTimeField(auto_now_add) | |

**`NotificationPreference`** — per-user settings
| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID PK | |
| `user` | OneToOneField(User, CASCADE) | |
| `email_digest` | CharField(DigestFrequency) | `none` / `daily` / `weekly` |
| `mute_all` | BooleanField(False) | |

### New Permission Key

Add `MODERATE_FORUM = "moderate_forum"` to `PermissionKey` in `backend/users/permissions.py`.

---

## 3. API Design

New router: `api.add_router("/forum/", forum_router)` in `config/urls.py`.

### Pagination Pattern (first in codebase)

```python
class PaginatedResponse(BaseModel):
    items: list
    count: int
    page: int
    page_size: int
    has_next: bool
```

Default `page_size=20`, max 50. Simple offset pagination (sufficient for <500 members).

### Endpoints

**Posts**
| Method | Path | Auth | Who | Description |
|--------|------|------|-----|-------------|
| GET | `/posts/` | JWT | member | Paginated feed. Params: `page`, `page_size`, `event_id` |
| POST | `/posts/` | JWT | member | Create post. Body: `{content, linked_event_id?}` |
| GET | `/posts/{id}/` | JWT | member | Post detail with first page of comments + reactions |
| PATCH | `/posts/{id}/` | JWT | author or mod | Update content |
| DELETE | `/posts/{id}/` | JWT | author or mod | Soft delete |
| POST | `/posts/{id}/pin/` | JWT | mod | Toggle pin |
| POST | `/posts/{id}/lock/` | JWT | mod or event host | Toggle lock |

**Comments**
| Method | Path | Auth | Who | Description |
|--------|------|------|-----|-------------|
| GET | `/posts/{id}/comments/` | JWT | member | Paginated, chronological |
| POST | `/posts/{id}/comments/` | JWT | member (if unlocked) | Body: `{content, parent_id?}` |
| PATCH | `/comments/{id}/` | JWT | author or mod | Update |
| DELETE | `/comments/{id}/` | JWT | author or mod | Soft delete |

**Reactions**
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/posts/{id}/react/` | JWT | Toggle reaction. Body: `{emoji}` |
| POST | `/comments/{id}/react/` | JWT | Toggle reaction on comment |

**Read Tracking & Notifications**
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/posts/{id}/read/` | JWT | Mark post as read |
| GET | `/unread-counts/` | JWT | `{total_unread, posts: [{post_id, count}]}` |
| GET | `/notifications/` | JWT | Paginated notifications |
| POST | `/notifications/read/` | JWT | Mark all/specific as read |
| GET | `/notifications/unread-count/` | JWT | `{count}` for badge |
| GET | `/notification-preferences/` | JWT | Get settings |
| PATCH | `/notification-preferences/` | JWT | Update settings |

### Key Schemas

**PostOut**: `id, author_id, author_name, content (delta), plain_text, linked_event_id, linked_event_title, is_pinned, is_locked, comment_count, unread_count, reaction_counts ({emoji: count}), my_reactions ([emoji]), created_at, updated_at`

**PostDetailOut**: extends PostOut + `comments: list[CommentOut]`

**CommentOut**: `id, author_id, author_name, content, plain_text, parent_id, reaction_counts, my_reactions, created_at, updated_at`

---

## 4. Frontend Architecture

### New Models (Freezed)
- `lib/models/forum_post.dart`
- `lib/models/forum_comment.dart`
- `lib/models/forum_notification.dart`

### New Providers
- `forum_provider.dart` — `forumFeedProvider` (paginated list), `forumPostDetailProvider` (family by ID), `eventDiscussionProvider` (family by event ID)
- `forum_notifier.dart` — `ForumNotifier` (AsyncNotifier, keepAlive) for mutations: create/edit/delete posts, create/edit/delete comments, react, mark read
- `notification_provider.dart` — `unreadNotificationCountProvider` (polled), `notificationsProvider`, `notificationPreferencesProvider`

### New Screens & Routes
| Route | Screen | Description |
|-------|--------|-------------|
| `/forum` | `ForumFeedScreen` | Main feed, compose FAB, pull-to-refresh |
| `/forum/compose` | `ForumComposeScreen` | Full-screen QuillContentEditor composer |
| `/forum/:postId` | `ForumPostScreen` | Post detail with comments, reactions |
| `/notifications` | `NotificationsScreen` | Notification list with mark-all-read |
| `/settings/notifications` | `NotificationSettingsScreen` | Digest frequency, mute toggle |

All protected routes requiring auth.

### Nav Integration
- **Wide nav**: add "forum" button between "calendar" and "my events"
- **Mobile drawer**: add forum drawer item
- **AppBar**: notification bell icon with unread badge (all screens when logged in)

### Rich Text
Reuse existing `QuillContentEditor` widget. Post content stored as Delta JSON (same as guidelines/FAQ/editable pages).

### Optimistic UI
- **Reactions**: immediately update local count + `myReactions`, revert on error
- **New comment**: append to local list with "sending" indicator, replace on success
- **Mark read**: update local unread count immediately, fire API in background

### Pagination UI
`ForumFeedScreen` uses `ListView.builder` with scroll listener to load next page. A `forumFeedStateProvider` (AsyncNotifier, keepAlive) accumulates posts across pages — establishes the pattern for future paginated lists.

---

## 5. Real-Time Strategy

| Option | Latency | Complexity | Infrastructure | Recommendation |
|--------|---------|------------|---------------|----------------|
| **Polling** | ~30s | Minimal | None | Phase 1-3 |
| **Centrifugo** | <1s | Low-Medium | Go binary on Railway, JWT auth | Phase 4 (recommended) |
| **SSE** | <1s | Medium | Uvicorn sidecar + PG LISTEN/NOTIFY | Alternative to Centrifugo |
| **WebSocket (Channels)** | <1s | High | Redis + ASGI migration | Not recommended |
| **External (Pusher/Firebase)** | <1s | Medium | External service | Fallback |

**Phase 1-3**: Poll `unread-counts` and `notifications/unread-count` every 30s via `Timer.periodic` in a keepAlive provider. At 500 concurrent users = ~17 req/s, well within capacity.

**Phase 4 (recommended): Centrifugo.** Deploy as a separate Railway service (~50MB Go binary, minimal RAM). Django publishes to Centrifugo's HTTP API after mutations; Flutter subscribes via the `centrifuge` Dart SDK. JWT auth is native — Django generates Centrifugo connection tokens using the same secret. No Redis, no ASGI migration. Free and open source (MIT).

**Alternative: SSE** via a lightweight Uvicorn sidecar process with PG LISTEN/NOTIFY. Simpler than Channels but more custom code than Centrifugo.

---

## 6. Phased Implementation Roadmap

### Phase 1: Core Forum MVP — **Large (2-3 weeks)**

Ship a usable forum. First paginated endpoint in the codebase.

- **Backend**: new `forum` app, `Post` + `Comment` models, CRUD + pin/lock endpoints, `MODERATE_FORUM` permission
- **Frontend**: `ForumPost`/`ForumComment` Freezed models, feed/detail/compose screens, forum nav item
- **Tests**: `test_forum.py`, widget tests, a11y tests
- **Dependencies**: none

### Phase 2: Engagement Features — **Medium (1-2 weeks)**

Reactions, mentions, richer interactions.

- **Backend**: `Reaction` model, react endpoints
- **Frontend**: `ReactionBar` widget (curated emoji picker), `MentionOverlay` for @mentions in composer, optimistic UI
- **Dependencies**: Phase 1

### Phase 3: Event-Linked Discussions (#57) — **Medium (1-2 weeks)**

Auto-create forum posts for events. RSVP'd users see discussion from event detail.

- **Backend**: modify event creation to auto-create linked Post, event host implicit lock permission
- **Frontend**: "Discussion (n comments)" button on event detail, `eventDiscussionProvider`
- **Dependencies**: Phase 1 (can run in parallel with Phase 2)

### Phase 4: Notifications & Real-Time — **Large (2-3 weeks)**

In-app notifications, polling, read tracking, email digests.

- **Backend**: `Notification`, `NotificationPreference`, `ReadReceipt` models, notification endpoints, `send_forum_digests` management command
- **Frontend**: notification bell badge, notifications screen, settings screen, 30s polling timer
- **Dependencies**: Phase 1

### Phase 5: Search, Moderation, Mobile Polish — **Medium-Large (2-3 weeks)**

Full-text search, reporting, moderation dashboard, mobile UX.

- **Backend**: `Report` model, PG `SearchVector` on `plain_text` (GIN index), search endpoint, report/resolve endpoints
- **Frontend**: search screen, moderation dashboard (admin), pull-to-refresh, swipe-to-reply, bottom sheet compose on mobile
- **Dependencies**: Phase 4

---

## 7. WhatsApp Migration Strategy

### Pre-Launch (Week -2 to -1)
- Seed forum with 3-5 starter posts (welcome, how-to, conversation starters)
- Test with 5-10 active members for feedback
- Draft WhatsApp announcement

### Parallel Running (Week 1-4)
- Announce forum on WhatsApp with link
- Cross-post important content to both platforms (weeks 1-2)
- Event discussions go forum-only from day 1 (concrete reason to use forum)
- Weekly "forum highlights" on WhatsApp

### Transition (Week 4-6)
- Stop cross-posting, WhatsApp becomes a redirect
- Pin final WhatsApp message with forum link and archive date
- Set WhatsApp group to announcement-only

### Post-Transition (Week 6+)
- Archive WhatsApp group (don't delete — preserves history)
- Hide/remove WhatsApp admin config screen
- Monitor engagement: weekly active users, posts/day, comments/day

---

## 8. Critical Files

| File | Relevance |
|------|-----------|
| `backend/community/models.py` | Reference for model patterns (UUID PKs, TextChoices, FK conventions), Event model |
| `backend/community/api.py` | Reference for endpoint patterns, event creation to modify for Phase 3 |
| `backend/users/permissions.py` | Add `MODERATE_FORUM` permission |
| `frontend/lib/router/app_router.dart` | Add forum routes + auth guards |
| `frontend/lib/widgets/app_scaffold.dart` | Add forum nav item + notification badge |
| `frontend/lib/widgets/quill_content_editor.dart` | Reuse for post/comment composition |
| `frontend/lib/config/constants.dart` | Add forum-related constants |

## 9. Verification

- `make test` passes after each phase
- `make frontend-test` passes
- `make ci` green before any merge
- Manual testing: create post, comment, react, check unread counts, verify event-linked discussion
