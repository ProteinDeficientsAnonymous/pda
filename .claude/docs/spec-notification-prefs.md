# spec: per-type notification preferences

_status: proposed · 2026-07-24 (rescoped 2026-08-01: push removed)_

Per-type opt-outs for the two delivery channels that exist today: the in-app bell (SSE) and
email. Push notifications were originally phases 3–5 of this spec and have been cut — there is
no push infrastructure in the repo (no service worker, no Capacitor shell, no FCM/APNs
dependency), and it isn't wanted. [spike-native-push.md](spike-native-push.md) and
[app-store-readiness.md](app-store-readiness.md) retain that research if it's ever revived.

## goals

1. Per-type notification opt-outs (e.g. "comments on events i'm going to", "invitations to
   events"), managed from the settings screen — each type toggleable independently for the
   **bell** and for **email**, where an email mirror exists.
2. Split `EVENT_COMMENT` into **hosting** vs **attending** variants so those are separately
   toggleable — and add the attending notification, which **does not exist today** (attendees
   currently get only a silent `event_updated` cache-refresh ping, no bell row).

## non-goals

- **Push notifications** of any kind. Cut from this spec.
- Preferences for **transactional/account emails** (login links, join approval, onboarding) —
  always on. Likewise emails to **non-members** (public RSVP confirmations/removals): no
  account, no prefs.
- Preferences for **event blasts** and **attendance-milestone reminder emails** — neither maps
  to a `NotificationType`. Deferred; adding them would loosen the model's key column from
  enum-validated to a known-keys list.
- Per-event mute ("stop notifying me about *this* event"). Future work; the model doesn't
  block it.
- Quiet hours, digests, batching.

## current architecture (context)

- `Notification` rows are the source of truth (`backend/notifications/models.py`), stamped with
  a `NotificationType` enum (15 values). All creation goes through
  `backend/notifications/service.py` — every `create_*`/`notify_*` function ends with
  `bulk_create(...)` + `_notify_users(ids)` (pg_notify → SSE → bell).
- SSE only works while a tab is foregrounded. That is a known limitation and this spec does not
  address it — a member who is not looking at the app sees the notification next time they open
  it, or gets the email where one exists.
- Silent `_ping_event_update` / `broadcast_*` calls create no rows and are unaffected.

---

## phase 1 — notification preferences (opt-outs)

Ships first: phase 2 adds a brand-new fan-out (attendee comment notifications), and the mute
switch should exist before the new noise does.

### model — `NotificationOptOut`

`backend/notifications/models.py` (append):

```python
class OptOutChannel(models.TextChoices):
    APP = "app", "App"        # bell row + SSE
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

An `app` opt-out suppresses the notification entirely (no bell row, no SSE announce). An
`email` opt-out suppresses the email mirror where one exists. The two are independent: a
member can keep the bell and mute the email, or the reverse.

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
opted-out users, SSE inherits the `app` preference for free — no checks in the delivery layer.

**Email call sites** — the member-facing emails that mirror a notification type check the
`email` channel before sending (same helper, `channel=OptOutChannel.EMAIL`):

| email | call site | notification type |
|---|---|---|
| event invite email | `community/_event_invite_email.py` | `event_invite` |
| co-host invite email | `community/_cohost_invite_helpers.py` | `cohost_invite` |
| check-in nudge email | `community/_checkin_nudge.py` | `checkin_nudge` |

Types **exempt from the settings UI** (but not from the mechanism): `join_request`,
`event_flagged`, `magic_link_request` — permission-routed operational notifications for admins,
not personal-interest ones. `checkin_nudge` and `rsvp_declined_note` are host-facing and
**always on** — a host needs to know who can't make it and that check-in is open; these are
part of running an event, not optional interest. `cohost_added` and (post-phase-2)
`event_comment` are legacy values that no longer get created; they never appear in the UI.

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
  all of its types. Each group has a "bell" toggle; groups whose type also sends an email get a
  second "email" toggle. Lowercase copy per house style:

| group label | notification types | email toggle |
|---|---|---|
| invitations to events | `event_invite` | yes |
| event cancellations | `event_cancelled` | — |
| waitlist promotions | `waitlist_promoted` | — |
| co-hosting (invites & changes) | `cohost_invite`, `cohost_invite_accepted`, `cohost_invite_declined`, `cohost_removed` | yes (`cohost_invite` only) |
| replies to your comments | `comment_reply` | — |
| comments on events you host | `event_comment_hosting` *(phase 2)* | — |
| comments on events you're going to | `event_comment_attending` *(phase 2)* | — |

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
- Host-facing types (`checkin_nudge`, `rsvp_declined_note`) cannot be opted out of via the API.
- Frontend: prefs section renders groups with bell/email toggles, toggle fires PUT with the
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

## rollout / pr breakdown

| pr | contents | depends on |
|---|---|---|
| 1 | `NotificationOptOut` model + enforcement helper + preferences API + settings UI | — |
| 2 | comment split: new enum values, `notify_event_comment` rewrite, frontend types/targets/labels | 1 |

Both are backend + a settings section, fully testable locally.

## open questions

1. RSVP confirmation emails (Issue 1143) are scoped to send on all status transitions,
   including waitlist promotion. They need a `NotificationType` to hang an email toggle on —
   `waitlist_promoted` already exists (and currently has **no producer at all**), but a plain
   "you're going" confirmation has no type yet. Decide whether that gets its own type here or
   in 1143.
