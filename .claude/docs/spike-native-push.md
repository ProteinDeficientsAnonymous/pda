# spike: native push (APNs) integration sketch

_design spike — not wired in yet. shows exactly how native push slots into the existing
`notifications` app for the Capacitor/App-Store path. SSE is untouched._

## the key observation

every one of the 13 `create_*_notification()` functions in `backend/notifications/service.py` ends
with the identical pattern:

```python
Notification.objects.create(...)   # or bulk_create([...])
_notify_users(ids)                 # SSE announce
```

so push is **one new helper, `_push_users(...)`, called on the line after `_notify_users`** — a
mechanical 1-line addition per function, no body rewrites. the `Notification` table stays the single
source of truth; SSE and APNs just announce that a row was created.

silent `event_updated` pings (`_ping_event_update` / `broadcast_*`) stay **SSE-only** — no rows, no
push.

---

## 1. model — `PushSubscription`

`backend/notifications/models.py` (append). follows project conventions: UUID PK, `created_at`,
`TextChoices`, explicit `on_delete` + `related_name`.

```python
class DevicePlatform(models.TextChoices):
    IOS = "ios", "iOS"
    ANDROID = "android", "Android"


class PushSubscription(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="push_subscriptions",
    )
    device_token = models.CharField(max_length=255)
    platform = models.CharField(
        max_length=16,
        choices=DevicePlatform.choices,
        default=DevicePlatform.IOS,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "device_token", "platform"],
                name="uniq_user_device_platform",
            )
        ]
        indexes = [models.Index(fields=["user"])]

    def __str__(self) -> str:
        return f"{self.platform} token for {self.user}"
```

then `make migrate`.

---

## 2. sender — `backend/notifications/_apns_sender.py`

mirrors the `email_sender.py` protocol/impl pattern already in the app (Protocol + real impl +
console fallback). token-based auth (`.p8` key) — recommended over certs.

```python
from __future__ import annotations

import logging
from typing import Protocol

logger = logging.getLogger(__name__)


class PushSender(Protocol):
    def send(self, *, token: str, title: str, body: str, data: dict[str, str]) -> bool: ...


class ConsoleSender:
    """Dev fallback — logs instead of hitting APNs."""

    def send(self, *, token: str, title: str, body: str, data: dict[str, str]) -> bool:
        logger.info("[push] -> %s | %s: %s | %s", token[:12], title, body, data)
        return True


class ApnsSender:
    """Production sender via APNs token auth (e.g. the `aioapns` or `apns2` lib)."""

    def __init__(self, *, key_p8: str, key_id: str, team_id: str, bundle_id: str, use_sandbox: bool):
        self._cfg = (key_p8, key_id, team_id, bundle_id, use_sandbox)
        # construct the APNs client here from settings

    def send(self, *, token: str, title: str, body: str, data: dict[str, str]) -> bool:
        # build the aps payload: {"aps": {"alert": {"title", "body"}, "badge", "sound"}, **data}
        # return False on InvalidToken / Unregistered so the caller can prune the row
        ...


def get_push_sender() -> PushSender:
    from django.conf import settings

    if getattr(settings, "APNS_KEY_P8", ""):
        return ApnsSender(
            key_p8=settings.APNS_KEY_P8,
            key_id=settings.APNS_KEY_ID,
            team_id=settings.APNS_TEAM_ID,
            bundle_id=settings.APNS_BUNDLE_ID,
            use_sandbox=not settings.IS_PRODUCTION,
        )
    return ConsoleSender()
```

settings additions (all empty placeholders in `.env.example`, per project rule):
`APNS_KEY_P8`, `APNS_KEY_ID`, `APNS_TEAM_ID`, `APNS_BUNDLE_ID`.

---

## 3. the helper — added to `service.py`

```python
def _push_users(
    user_ids: Iterable[str],
    *,
    title: str,
    body: str,
    event_id: str | None = None,
) -> None:
    """Send a native push to every registered device for these users.

    Background-state counterpart to `_notify_users` (which is SSE/foreground).
    The Notification row is already written by the caller; this only announces.
    Prunes tokens APNs rejects as invalid.
    """
    from .models import PushSubscription
    from ._apns_sender import get_push_sender

    ids = [str(uid) for uid in user_ids]
    if not ids:
        return

    sender = get_push_sender()
    data = {"event_id": event_id} if event_id else {}
    dead: list[str] = []
    for sub in PushSubscription.objects.filter(user_id__in=ids):
        ok = sender.send(token=sub.device_token, title=title, body=body, data=data)
        if not ok:
            dead.append(sub.id)
    if dead:
        PushSubscription.objects.filter(id__in=dead).delete()
```

### how a call site changes (example: event invite)

`create_event_invite_notifications` — the only new line is the `_push_users(...)` call:

```python
    Notification.objects.bulk_create([...])   # unchanged
    _notify_users(notified_ids)               # unchanged (SSE / foreground)
    _push_users(                              # NEW (APNs / background)
        notified_ids,
        title="new invite",
        body=f"{inviter_name} invited you to {event.title}",
        event_id=str(event.pk),
    )
```

repeat the one-line add for the other 12 functions, reusing each function's existing `message` string
as the push `body`. (a small refactor option: have each function build a `(title, body)` once and pass
it to both — but the literal 1-line-per-function add is the lowest-risk first pass.)

> note: push `title`/`body` are user-facing → must be **lowercase** per the frontend-text rule if they
> ever surface in-app; APNs banner text follows the same house style.

---

## 4. endpoints — `backend/notifications/api.py`

standard Django Ninja, `JWTAuth`, tuple returns, `{"detail": ...}` errors.

```python
class PushSubscribeIn(Schema):
    device_token: str
    platform: str = DevicePlatform.IOS

@router.post("/push/subscribe/", auth=JWTAuth(), response={200: MessageOut, 400: ErrorOut})
def subscribe_push(request, data: PushSubscribeIn):
    if data.platform not in DevicePlatform.values:
        return 400, {"detail": "invalid platform"}
    PushSubscription.objects.update_or_create(
        user=request.auth,
        device_token=data.device_token,
        platform=data.platform,
        defaults={},
    )
    return 200, {"message": "subscribed"}

@router.post("/push/unsubscribe/", auth=JWTAuth(), response={200: MessageOut})
def unsubscribe_push(request, data: PushSubscribeIn):
    PushSubscription.objects.filter(
        user=request.auth, device_token=data.device_token
    ).delete()
    return 200, {"message": "unsubscribed"}
```

also: **delete the user's tokens on logout** (in the logout endpoint) for privacy + correctness.

---

## 5. client — `@capacitor/push-notifications`

wired once at app startup (e.g. in `AppShell` or an auth effect). suppressing the foreground banner is
what prevents double-notification with SSE.

```ts
import { PushNotifications } from '@capacitor/push-notifications';
import { Capacitor } from '@capacitor/core';

export async function initPush() {
  if (Capacitor.getPlatform() === 'web') return; // web uses SSE only

  const perm = await PushNotifications.requestPermissions();
  if (perm.receive !== 'granted') return;
  await PushNotifications.register();

  PushNotifications.addListener('registration', (t) =>
    api.post('/notifications/push/subscribe/', { device_token: t.value, platform: 'ios' }),
  );

  // foreground: SSE already updated the UI → swallow the banner, just refresh caches
  PushNotifications.addListener('pushNotificationReceived', () => {
    queryClient.invalidateQueries({ queryKey: ['notifications'] });
    queryClient.invalidateQueries({ queryKey: ['unread-count'] });
  });

  // background tap → deep-link into the event (reuses Universal Links routing)
  PushNotifications.addListener('pushNotificationActionPerformed', ({ notification }) => {
    const eventId = notification.data?.event_id;
    if (eventId) router.navigate(`/events/${eventId}`);
  });
}
```

call `initPush()` after login; on logout, `POST /notifications/push/unsubscribe/` then
`PushNotifications.removeAllListeners()`.

---

## build order

1. model + migration (`PushSubscription`) — safe, no behavior change.
2. `_apns_sender.py` with `ConsoleSender` fallback — testable without Apple creds.
3. `_push_users()` helper + wire the 13 call sites — push fires to console in dev.
4. subscribe/unsubscribe endpoints + logout cleanup.
5. Apple side: APNs `.p8` key, Push capability on the App ID, real `ApnsSender`.
6. client `initPush()` + Capacitor plugin.

steps 1–4 are pure backend and fully testable with the console sender before any Apple account exists.
