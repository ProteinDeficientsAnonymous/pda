# spec: push notifications + per-type notification preferences

_status: proposed · 2026-07-24_

Builds on [app-store-readiness.md](app-store-readiness.md) (path A: Capacitor wrap) and
[spike-native-push.md](spike-native-push.md) (APNs sketch). This spec supersedes the spike's
sender choice (FCM instead of raw APNs — see §6) and adds two things the spike didn't cover:
web push (so notifications work before any app store exists) and per-type user preferences.

## goals

1. Real push notifications when the app is closed — **web push first** (no app store, ships in
   days), Capacitor iOS/Android later. All backend infrastructure is shared between the two.
2. Per-type notification opt-outs (e.g. "comments on events i'm going to", "invitations to
   events"), managed from the settings screen — with a separate **email** toggle for the types
   that also send an email (event invites, co-host invites, check-in nudges).
3. Split `EVENT_COMMENT` into **hosting** vs **attending** variants so those are separately
   toggleable — and add the attending notification, which **does not exist today** (attendees
   currently get only a silent `event_updated` cache-refresh ping, no bell row).

## non-goals

- Preferences for **transactional/account emails** (login links, join approval, onboarding) —
  always on. Likewise emails to **non-members** (public RSVP confirmations/removals): no
  account, no prefs.
- Preferences for **event blasts** and **attendance-milestone reminder emails** — neither maps
  to a `NotificationType`. The channel model doesn't preclude adding email-only pref keys for
  them later (see open questions).
- Per-event mute ("stop notifying me about *this* event"). Future work; the model doesn't
  block it.
- Quiet hours, digests, batching.

## current architecture (context)

- `Notification` rows are the source of truth (`backend/notifications/models.py`), stamped with
  a `NotificationType` enum (15 values). All creation goes through
  `backend/notifications/service.py` — every `create_*`/`notify_*` function ends with
  `bulk_create(...)` + `_notify_users(ids)` (pg_notify → SSE → bell).
- SSE only works while a tab/app is foregrounded. Push is a new, additive delivery channel;
  SSE stays untouched.
- Silent `_ping_event_update` / `broadcast_*` calls create no rows and will never push.

---

## phase 1 — notification preferences (opt-outs)

Ships first: phase 2 adds a brand-new fan-out (attendee comment notifications), and the mute
switch should exist before the new noise does.

### model — `NotificationOptOut`

`backend/notifications/models.py` (append):

```python
class OptOutChannel(models.TextChoices):
    APP = "app", "App"        # bell row + SSE + (future) push
    EMAIL = "email", "Email"  # the email mirror of this notification type


class NotificationOptOut(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="notification_opt_outs"
    )
    notification_type = models.CharField(max_length=32, choices=NotificationType.choices)
    channel = models.CharField(max_length=8, choices=OptOutChannel.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "notification_type", "channel"],
                name="uniq_user_notification_opt_out",
            )
        ]
```

Opt-outs only — absence of a row means enabled. No default rows to backfill, and new
notification types are automatically on for everyone.

Two channels, not three: an `app` opt-out suppresses the notification entirely (no bell row,
no SSE announce, no future push — one switch, since push is just delivery of the same row).
An `email` opt-out suppresses the email mirror where one exists.
`# ponytail: bell+push share one channel; split them only if "push off, bell on" is requested`

### enforcement — one helper in `service.py`

```python
def _after_opt_outs(
    user_ids: Iterable[str], ntype: str, channel: str = OptOutChannel.APP
) -> list[str]:
    ids = [str(u) for u in user_ids]
    if not ids:
        return ids
    opted_out = set(
        str(u)
        for u in NotificationOptOut.objects.filter(
            user_id__in=ids, notification_type=ntype, channel=channel
        ).values_list("user_id", flat=True)
    )
    return [u for u in ids if u not in opted_out]
```

Each `create_*`/`notify_*` function filters its recipient list through this before
`bulk_create`. One added line per function (~13 sites). Because rows are never created for
opted-out users, SSE and (later) push inherit the `app` preference for free — no per-channel
checks in the delivery layer.

**Email call sites** — the three member-facing emails that mirror a notification type check
the `email` channel before sending (same helper, `channel=OptOutChannel.EMAIL`):

| email | call site | notification type |
|---|---|---|
| event invite email | `community/_event_invite_email.py` | `event_invite` |
| co-host invite email | `community/_cohost_invite_helpers.py` | `cohost_invite` |
| check-in nudge email | `community/_checkin_nudge.py` | `checkin_nudge` |

Types **exempt from the settings UI** (but not from the mechanism): `join_request`,
`event_flagged`, `magic_link_request` — these are permission-routed operational notifications
for admins, not personal-interest ones. `cohost_added` and (post-phase-2) `event_comment` are
legacy values that no longer get created; they never appear in the UI.

### api — `backend/notifications/api.py`

```python
class PreferencesOut(Schema):
    opted_out_app: list[str]
    opted_out_email: list[str]

@router.get("/preferences/", auth=JWTAuth(), response=PreferencesOut)
@router.put("/preferences/", auth=JWTAuth(), response={200: PreferencesOut, 400: ErrorOut})
```

- `GET` returns the user's opted-out types per channel.
- `PUT` replaces the full set (validate every value against `NotificationType.values` → 400 on
  unknown; then `transaction.atomic()`: delete user's rows, `bulk_create` the new set).
  Full-replace beats per-toggle endpoints: one round trip, idempotent, trivial to test.

Regenerate types: `make frontend-types`.

### frontend — settings section

- New sibling component `frontend/src/screens/settings/NotificationPrefs.tsx` (SettingsScreen
  is 344 lines — do not inline; follow the `PrivacyToggles.tsx` pattern).
- Query + mutation hooks in `frontend/src/api/notifications.ts`
  (`useNotificationPreferences`, `useUpdateNotificationPreferences`), optimistic toggle.
- The UI renders **groups**, each mapping to one or more enum values. Toggling a group writes
  all of its types. Each group has an "app" toggle; groups whose type also sends an email get
  a second "email" toggle. Lowercase copy per house style:

| group label | notification types | email toggle |
|---|---|---|
| invitations to events | `event_invite` | yes |
| event cancellations | `event_cancelled` | — |
| waitlist promotions | `waitlist_promoted` | — |
| co-hosting (invites & changes) | `cohost_invite`, `cohost_invite_accepted`, `cohost_invite_declined`, `cohost_removed` | yes (`cohost_invite` only) |
| replies to your comments | `comment_reply` | — |
| comments on events you host | `event_comment_hosting` *(phase 2)* | — |
| comments on events you're going to | `event_comment_attending` *(phase 2)* | — |
| can't-go notes on your events | `rsvp_declined_note` | — |
| check-in reminders for events you host | `checkin_nudge` | yes |

A toggle renders "on" only when *none* of its group's types are opted out on that channel.
Section intro copy, e.g.: "choose what you get notified about — everything's on unless you
turn it off".

### tests

- API: get empty default, put + re-get roundtrip, unknown type → 400, replace semantics,
  channels independent.
- Service: opted-out user excluded from `bulk_create` and `_notify_users`; other recipients
  unaffected; opt-out of one type/channel doesn't touch another.
- Email: each of the three email call sites skips opted-out recipients; `app` opt-out alone
  doesn't suppress the email (and vice versa).
- Frontend: prefs section renders groups with app/email toggles, toggle fires PUT with the
  full per-channel type sets.

---

## phase 2 — split event comment notifications (hosting vs attending)

### backend

`NotificationType` gains:

```python
EVENT_COMMENT_HOSTING = "event_comment_hosting", "Event Comment (Hosting)"
EVENT_COMMENT_ATTENDING = "event_comment_attending", "Event Comment (Attending)"
```

`EVENT_COMMENT` stays in the enum as legacy (existing rows keep rendering — same precedent as
`COHOST_ADDED`). No data migration.

`notify_event_comment` (service.py) changes:

- **hosts:** current recipients (creator + co-hosts, excluding author) now get
  `EVENT_COMMENT_HOSTING`. Message unchanged.
- **attendees (new):** members with an `ATTENDING` or `MAYBE` RSVP — matching the
  cancellation-notification audience — excluding the author and anyone already in the hosts
  set, get `EVENT_COMMENT_ATTENDING` with the same message. Invited-but-unresponded users are
  *not* included (they haven't committed to the event; a comment ping would be noise).
- Both lists pass through `_after_opt_outs` with their respective type.
- Still top-level comments only (replies keep routing through `notify_comment_reply`).
- Public (non-member) RSVPs have no user account and are unaffected.

### frontend

- `frontend/src/models/notification.ts`: add `EventCommentHosting` / `EventCommentAttending`
  constants (keep `EventComment` as legacy).
- `frontend/src/layout/notificationTarget.ts`: both new types → `/events/{eventId}`, same as
  the legacy case (which stays).
- Prefs label map: the two comment groups from the phase-1 table light up.

### tests

- Host + co-hosts receive `event_comment_hosting`; attending + maybe members receive
  `event_comment_attending`; author, hosts-in-attendee-set, declined, invited-only, and
  public RSVPs receive nothing.
- Opt-outs respected independently per type.
- `notificationTarget` cases for both new types + legacy.

---

## phase 3 — web push (PWA)

Works on Android Chrome and desktop browsers immediately; on iOS Safari 16.4+ **only when the
site is added to the home screen** (requires a web app manifest). This is the
no-app-store path — everything here is also the substrate for phase 4.

### model — `PushSubscription`

As sketched in the spike, with two adjustments for web:

```python
class DevicePlatform(models.TextChoices):
    WEB = "web", "Web"
    IOS = "ios", "iOS"
    ANDROID = "android", "Android"


class PushSubscription(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="push_subscriptions"
    )
    # web: the PushSubscription JSON (endpoint + keys); native: the FCM token
    token = models.TextField()
    platform = models.CharField(max_length=16, choices=DevicePlatform.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "token"], name="uniq_user_push_token")
        ]
        indexes = [models.Index(fields=["user"])]
```

(`TextField`, not `CharField(255)` — a web push subscription JSON easily exceeds 255 chars.)

### sender — `backend/notifications/_push_sender.py`

Protocol + impl + console fallback, mirroring `email_sender.py` (and the spike):

- `WebPushSender` via the `pywebpush` library (add to backend deps). VAPID auth.
- `ConsoleSender` when keys are unset — dev works with zero config.
- Returns `False` on `404`/`410` (subscription gone) so the caller prunes the row.

Settings/env (empty placeholders in `.env.example` per project rule): `VAPID_PUBLIC_KEY`,
`VAPID_PRIVATE_KEY`, `VAPID_CLAIMS_EMAIL`. Public key also exposed via a tiny
`GET /api/notifications/push/vapid-key/` endpoint (unauthenticated is fine — it's public).

### service hook — `_push_users` in `service.py`

Per the spike: called on the line after `_notify_users` in each of the ~13 creation functions,
reusing the function's existing `message` as the push body (title: `"pda"`), plus a `url` from
a small server-side target map (the only targets needed are `/events/{id}`,
`/events/{id}/attendance`, `/join-requests`, `/admin/...` — a ~15-line mirror of
`notificationTarget.ts`). Prunes dead subscriptions on failure.

Because opt-outs already filtered the recipient list at creation (phase 1), `_push_users`
needs **no preference logic**.

Delivery is a sequential in-request loop wrapped in `transaction.on_commit`.
`# ponytail: in-request sequential send; move to a background queue if send latency shows up`

### endpoints

Per the spike (`POST /push/subscribe/`, `POST /push/unsubscribe/`), with `token` +
`platform` in the body. Delete the user's subscriptions on logout.

### frontend

- `frontend/public/sw.js` — a plain hand-written service worker, ~30 lines, no workbox/PWA
  plugin: `push` event → `showNotification(title, {body, data:{url}})`; `notificationclick` →
  `clients.openWindow(url)`.
- `frontend/public/manifest.webmanifest` — name, icons, `display: standalone`,
  `start_url: /` (required for iOS home-screen install; also makes Android offer install).
- Settings: a "push notifications on this device" toggle at the top of the
  `NotificationPrefs` section — on: register SW → `Notification.requestPermission()` →
  `pushManager.subscribe({applicationServerKey})` → POST subscribe; off: unsubscribe both
  sides. Show a hint on iOS Safari when not installed: "add pda to your home screen to enable
  push".
- Foreground double-notification: SSE already updates the bell while the tab is open. Simplest
  guard — the SW skips `showNotification` when a window client is focused
  (`clients.matchAll` check).

### tests

- Subscribe/unsubscribe endpoints (auth required, dedupe on re-subscribe, logout cleanup).
- `_push_users`: sends to each subscription, prunes on failure, no-ops with no subscriptions,
  console sender path.
- SSE tests untouched (this is additive).

---

## phase 4 — capacitor native wrap (later)

Covered by [app-store-readiness.md](app-store-readiness.md) §path-A and the client section of
[spike-native-push.md](spike-native-push.md). Delta from the spike:

- **Use FCM for both iOS and Android** instead of a raw APNs sender — one `firebase-admin`
  integration covers both platforms (FCM proxies APNs; the APNs `.p8` key is uploaded to the
  Firebase console, not handled in our code). Adds an `FcmSender` beside `WebPushSender`
  behind the same protocol; `_push_users` dispatches on `platform`.
- `@capacitor/push-notifications` registers and POSTs the FCM token to the *same*
  `/push/subscribe/` endpoint with `platform: "ios" | "android"`.
- Foreground suppression + deep-link tap handling per the spike's `initPush()` sketch.
- Everything else (Apple Developer account, signing, store review) is process, not code.

---

## rollout / pr breakdown

| pr | contents | depends on |
|---|---|---|
| 1 | `NotificationOptOut` model + enforcement helper + preferences API + settings UI | — |
| 2 | comment split: new enum values, `notify_event_comment` rewrite, frontend types/targets/labels | 1 |
| 3 | `PushSubscription` model + `_push_sender.py` (webpush + console) + `_push_users` wiring + endpoints | 1 |
| 4 | service worker + manifest + settings push toggle | 3 |
| 5+ | capacitor wrap + FCM sender (its own project) | 3 |

PRs 1–3 are pure backend + a settings section, fully testable locally (console sender, no
VAPID keys needed). PR 4 is verifiable on any Chrome profile against localhost.

## open questions

1. Should `checkin_nudge` / `rsvp_declined_note` (host-facing) be exposed as toggles, or
   always-on for hosts? Spec says exposed — cheap to remove from the label map if not.
2. Push title: flat `"pda"` vs. per-type titles ("new invite", "new comment"). Spec defaults
   to flat; per-type titles are a string map away.
3. iOS home-screen-install friction: worth an in-app banner nudging install, or leave it to
   the settings hint? Spec says settings hint only, for now.
4. Attendance-milestone reminder emails and event blasts have no `NotificationType`, so they
   have no toggle in v1. If members should be able to opt out of those emails too, add
   email-only pref keys (e.g. `milestone_reminder`, `event_blast`) — the model's key column
   would loosen from enum-validated to a known-keys list. Deferred until asked for.
