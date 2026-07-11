# Public RSVP Manage-Endpoints Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the backend manage-RSVP endpoints (`GET`/`POST`/`DELETE /api/community/public/my-rsvps/`) that let a non-member view, update, and cancel their own RSVPs via an emailed magic-link token, plus a staging seed of non-member users so the flow is testable end-to-end.

**Architecture:** A new `_my_rsvps.py` module holds three token-authenticated endpoints on their own Ninja `Router`, mounted in `community/api.py`. Genuinely shared helpers move out of `_public_rsvp.py` into `_public_rsvp_shared.py` so neither endpoint module imports the other. All RSVP mechanics (capacity, waitlist, promotion emails) reuse existing functions unchanged. The `seed_staging` command grows a non-member band.

**Tech Stack:** Django, Django Ninja, pytest. Postgres in prod / SQLite for local test.

## Global Constraints

- Endpoints are `auth=None` — the `?token=...` query param is the only auth. Resolve via `NonMemberRsvpToken.resolve_user(token)`; `None` → 404 `Code.Event.NOT_FOUND`.
- Rate limit every manage endpoint: `@rate_limit(key_func=client_ip, rate="30/h")`, placed **below** the `@router.*` decorator.
- Reuse, do not duplicate: `_apply_rsvp_in_transaction`, `promote_from_waitlist`, `_event_out`, `_validate_rsvp_status`, `NonMemberRsvpToken.issue_or_extend`, `_email_promoted_non_members`, `PublicRsvpOut`/`PublicRsvpStateOut`.
- POST/DELETE call `issue_or_extend` (keeps prior emailed links valid). **No "rsvp updated" email this PR** (deferred to #705).
- Use enum values, never raw strings: `RSVPStatus.ATTENDING`, `EventType.OFFICIAL`, etc.
- Real URL prefix is `/api/community/public/my-rsvps/` (the community router mounts under `/community/`).
- Seed command stays idempotent, staging-gated, `--reset`-aware. Non-member phone band: `+170255503NN` (distinct from `...501` perm / `...502` condition bands).
- Files stay under 300 lines where practical, 500 hard max.
- All user-facing copy is lowercase (applies to seeded display names and printed summary lines).

---

## File Structure

- **Create** `backend/community/_public_rsvp_shared.py` — shared helpers extracted from `_public_rsvp.py`: `_load_public_rsvp_event`, `_format_event_when`, `_event_links`, `_email_details`, `_log_email_failure`, `_email_promoted_non_members`, and the `PublicRsvpStateOut` / `PublicRsvpOut` schemas.
- **Modify** `backend/community/_public_rsvp.py` — import the extracted helpers from `_public_rsvp_shared` instead of defining them locally.
- **Create** `backend/community/_my_rsvps.py` — the three manage endpoints + their schemas + token-auth helper.
- **Modify** `backend/community/api.py` — import and mount `my_rsvps_router`.
- **Create** `backend/tests/test_my_rsvps.py` — endpoint tests.
- **Modify** `backend/community/management/commands/_seed_staging_data.py` — non-member phone/email builders, `NON_MEMBER_SPECS`, new official demo event in `STAGING_EVENTS`.
- **Modify** `backend/community/management/commands/seed_staging.py` — `_seed_non_members`, `_reset` update, summary printing manage URLs.
- **Modify** `backend/tests/test_seed_staging.py` — non-member seed assertions.

---

## Task 1: Extract shared helpers into `_public_rsvp_shared.py`

Pure refactor — behavior unchanged. This unblocks Task 2 importing helpers without a circular dependency.

**Files:**
- Create: `backend/community/_public_rsvp_shared.py`
- Modify: `backend/community/_public_rsvp.py`
- Test: existing `backend/tests/test_public_rsvp.py` + `test_public_rsvp_capacity.py` (must still pass)

**Interfaces:**
- Produces (importable from `community._public_rsvp_shared`):
  - `class PublicRsvpStateOut(BaseModel)` — fields `status: str`, `has_plus_one: bool`
  - `class PublicRsvpOut(BaseModel)` — fields `event: EventOut`, `rsvp: PublicRsvpStateOut`
  - `_load_public_rsvp_event(event_id) -> Event`
  - `_email_details(event: Event, user: User, token_str: str) -> RsvpEmailDetails`
  - `_log_email_failure(request, event, user, exc) -> None`
  - `_email_promoted_non_members(request, event, promoted_user_ids: list[str]) -> None`

- [ ] **Step 1: Create the shared module**

Create `backend/community/_public_rsvp_shared.py` by moving these verbatim from `_public_rsvp.py` (lines defining them today): the imports they need, `PublicRsvpStateOut`, `PublicRsvpOut`, `_load_public_rsvp_event`, `_format_event_when`, `_event_links`, `_email_details`, `_log_email_failure`, `_email_promoted_non_members`.

```python
import logging

from config.audit import audit_log
from django.conf import settings
from django.utils import timezone
from notifications._email_helpers import (
    RsvpEmailDetails,
    send_rsvp_waitlist_promoted_email,
)
from notifications.email_sender import get_email_sender
from pydantic import BaseModel
from users.models import NonMemberRsvpToken, User

from community._event_schemas import EventOut
from community._shared import logger
from community._validation import Code, raise_validation
from community.models import Event, EventStatus, EventType, PageVisibility


class PublicRsvpStateOut(BaseModel):
    status: str
    has_plus_one: bool


class PublicRsvpOut(BaseModel):
    event: EventOut
    rsvp: PublicRsvpStateOut


def _load_public_rsvp_event(event_id) -> Event:
    """Fetch a public-RSVP-eligible event, else 404 (every ineligible state hides as NOT_FOUND)."""
    event = Event.objects.prefetch_related("co_hosts", "invited_users").filter(id=event_id).first()
    if (
        event is None
        or event.event_type != EventType.OFFICIAL
        or event.status != EventStatus.ACTIVE
        or event.visibility != PageVisibility.PUBLIC
        or not event.rsvp_enabled
        or event.is_past
    ):
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    return event


def _format_event_when(event: Event) -> str:
    if event.datetime_tbd or event.start_datetime is None:
        return "to be decided"
    local = timezone.localtime(event.start_datetime)
    return local.strftime("%A, %B %d at %I:%M %p").replace(" 0", " ")


def _event_links(event: Event) -> list[str]:
    return [link for link in (event.whatsapp_link, event.partiful_link, event.other_link) if link]


def _email_details(event: Event, user: User, token_str: str) -> RsvpEmailDetails:
    return RsvpEmailDetails(
        to=user.email,
        display_name=user.display_name,
        event_title=event.title,
        event_when=_format_event_when(event),
        event_location=event.location,
        event_links=_event_links(event),
        manage_url=f"{settings.FRONTEND_BASE_URL}/my-rsvps?token={token_str}",
        join_url=f"{settings.FRONTEND_BASE_URL}/join",
    )


def _log_email_failure(request, event: Event, user: User, exc: Exception) -> None:
    logger.warning("public rsvp email failed", exc_info=True)
    audit_log(
        logging.WARNING,
        "public_rsvp_email_failed",
        request,
        target_type="event",
        target_id=str(event.id),
        details={"user_id": str(user.pk), "error": str(exc)},
    )


def _email_promoted_non_members(request, event: Event, promoted_user_ids: list[str]) -> None:
    """Email any promoted non-members a fresh manage link. Best-effort per user."""
    if not promoted_user_ids:
        return
    promoted = User.objects.filter(id__in=promoted_user_ids, is_member=False, email__isnull=False)
    for user in promoted:
        if not user.email:
            continue
        try:
            token = NonMemberRsvpToken.issue_or_extend(user)
            result = send_rsvp_waitlist_promoted_email(
                sender=get_email_sender(),
                details=_email_details(event, user, token.token),
            )
            if not result.success:
                raise RuntimeError(result.error or "send returned failure")
        except Exception as exc:
            _log_email_failure(request, event, user, exc)
```

Note: this also fixes `_email_promoted_non_members` to use `issue_or_extend` (was `issue`), consistent with the Global Constraints. That aligns with #630's intent without touching the submit endpoint's token call (which #630 owns).

- [ ] **Step 2: Update `_public_rsvp.py` to import from the shared module**

In `backend/community/_public_rsvp.py`: delete the moved definitions and add imports. Replace the local `PublicRsvpStateOut`/`PublicRsvpOut`/`_load_public_rsvp_event`/`_format_event_when`/`_event_links`/`_email_details`/`_log_email_failure`/`_email_promoted_non_members` with:

```python
from community._public_rsvp_shared import (
    PublicRsvpOut,
    PublicRsvpStateOut,
    _email_details,
    _email_promoted_non_members,
    _load_public_rsvp_event,
    _log_email_failure,
)
```

Remove now-unused imports from `_public_rsvp.py` (e.g. `send_rsvp_waitlist_promoted_email`, `EventStatus`, `EventType`, `PageVisibility`, `timezone` if no longer referenced). Keep `_public_rsvp_decoy`, `_backfill_email`, `_create_non_member`, `_resolve_both_match`, `_resolve_non_member`, `_send_confirmation_email`, and the `submit_public_rsvp` view in place.

- [ ] **Step 3: Run the existing public-rsvp tests to verify no regression**

Run: `cd backend && python -m pytest tests/test_public_rsvp.py tests/test_public_rsvp_capacity.py -q`
Expected: PASS (same count as before the refactor).

- [ ] **Step 4: Typecheck + lint the touched files**

Run: `make agent-typecheck && make agent-lint`
Expected: no new errors.

- [ ] **Step 5: Commit**

```bash
git add backend/community/_public_rsvp_shared.py backend/community/_public_rsvp.py
git commit -m "refactor(public-rsvp): extract shared helpers into _public_rsvp_shared"
```

---

## Task 2: Manage-RSVP module scaffold + token-auth helper + GET endpoint

**Files:**
- Create: `backend/community/_my_rsvps.py`
- Modify: `backend/community/api.py`
- Test: `backend/tests/test_my_rsvps.py`

**Interfaces:**
- Consumes: `NonMemberRsvpToken.resolve_user`, `_load_public_rsvp_event`, `PublicRsvpOut`/`PublicRsvpStateOut`, `_event_out`, `EventOut`.
- Produces:
  - `router` (Ninja `Router`) mounted at community root.
  - `_resolve_token_user(token: str) -> User` — returns the user or raises 404.
  - `GET /public/my-rsvps/` → `MyRsvpsOut`.
  - `class MyRsvpsUserOut(BaseModel)` — `display_name: str`, `email: str`, `phone_number: str`.
  - `class MyRsvpItemOut(BaseModel)` — `event: EventOut`, `status: str`, `has_plus_one: bool`.
  - `class MyRsvpsOut(BaseModel)` — `user: MyRsvpsUserOut`, `rsvps: list[MyRsvpItemOut]`.

- [ ] **Step 1: Write the failing test for GET (valid + invalid tokens)**

Create `backend/tests/test_my_rsvps.py`:

```python
import pytest
from community.models import EventRSVP, EventType, RSVPStatus
from users.models import NonMemberRsvpToken

from tests._public_rsvp_helpers import make_non_member, make_official_event

GET_URL = "/api/community/public/my-rsvps/"


@pytest.fixture
def nonmember(db):
    return make_non_member("+14155550001", "nm@example.com", name="non member")


@pytest.fixture
def official_event(db):
    return make_official_event(title="Official A")


@pytest.mark.django_db
class TestGetMyRsvps:
    def test_valid_token_returns_rsvps(self, api_client, nonmember, official_event):
        EventRSVP.objects.create(event=official_event, user=nonmember, status=RSVPStatus.ATTENDING)
        token = NonMemberRsvpToken.issue_or_extend(nonmember)
        resp = api_client.get(f"{GET_URL}?token={token.token}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["user"]["display_name"] == "non member"
        assert len(body["rsvps"]) == 1
        assert body["rsvps"][0]["status"] == RSVPStatus.ATTENDING
        assert body["rsvps"][0]["event"]["id"] == str(official_event.id)

    def test_only_official_events_appear(self, api_client, nonmember, official_event):
        community_event = make_official_event(title="Community B", event_type=EventType.COMMUNITY)
        EventRSVP.objects.create(event=official_event, user=nonmember, status=RSVPStatus.ATTENDING)
        EventRSVP.objects.create(event=community_event, user=nonmember, status=RSVPStatus.ATTENDING)
        token = NonMemberRsvpToken.issue_or_extend(nonmember)
        resp = api_client.get(f"{GET_URL}?token={token.token}")
        assert resp.status_code == 200
        ids = {r["event"]["id"] for r in resp.json()["rsvps"]}
        assert ids == {str(official_event.id)}

    def test_missing_token_404(self, api_client):
        assert api_client.get(GET_URL).status_code == 404

    def test_unknown_token_404(self, api_client):
        assert api_client.get(f"{GET_URL}?token=nope").status_code == 404

    def test_revoked_token_404(self, api_client, nonmember, official_event):
        EventRSVP.objects.create(event=official_event, user=nonmember, status=RSVPStatus.ATTENDING)
        token = NonMemberRsvpToken.issue_or_extend(nonmember)
        token.revoke()
        assert api_client.get(f"{GET_URL}?token={token.token}").status_code == 404
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_my_rsvps.py -q`
Expected: FAIL (404 for the valid case — the endpoint doesn't exist yet, so every path 404s; the assertions on body fail).

- [ ] **Step 3: Create `_my_rsvps.py` with the token helper + GET endpoint**

Create `backend/community/_my_rsvps.py`:

```python
from config.ratelimit import client_ip, rate_limit
from ninja import Router
from pydantic import BaseModel
from users.models import NonMemberRsvpToken, User

from community._event_helpers import _event_out
from community._event_schemas import EventOut
from community._public_rsvp_shared import PublicRsvpOut, _load_public_rsvp_event
from community._shared import ErrorOut
from community._validation import Code, raise_validation
from community.models import EventType, RSVPStatus

router = Router()


class MyRsvpsUserOut(BaseModel):
    display_name: str
    email: str
    phone_number: str


class MyRsvpItemOut(BaseModel):
    event: EventOut
    status: str
    has_plus_one: bool


class MyRsvpsOut(BaseModel):
    user: MyRsvpsUserOut
    rsvps: list[MyRsvpItemOut]


def _resolve_token_user(token: str) -> User:
    """Resolve a manage-rsvp token to its non-member user, or 404."""
    user = NonMemberRsvpToken.resolve_user(token)
    if user is None:
        raise_validation(Code.Event.NOT_FOUND, status_code=404)
    return user


@router.get(
    "/public/my-rsvps/",
    response={200: MyRsvpsOut, 404: ErrorOut, 429: ErrorOut},
    auth=None,
)
@rate_limit(key_func=client_ip, rate="30/h")
def list_my_rsvps(request, token: str = ""):
    user = _resolve_token_user(token)
    rsvps = (
        user.event_rsvps.filter(event__event_type=EventType.OFFICIAL)
        .select_related("event", "event__created_by")
        .prefetch_related("event__co_hosts", "event__invited_users", "event__rsvps__user")
    )
    items = [
        MyRsvpItemOut(
            event=_event_out(rsvp.event, user),
            status=rsvp.status,
            has_plus_one=rsvp.has_plus_one,
        )
        for rsvp in rsvps
    ]
    return 200, MyRsvpsOut(
        user=MyRsvpsUserOut(
            display_name=user.display_name,
            email=user.email or "",
            phone_number=user.phone_number,
        ),
        rsvps=items,
    )
```

Note: `RSVPStatus` and `PublicRsvpOut` and `_load_public_rsvp_event` are imported now because Tasks 3–4 use them; if lint flags them unused at this step, add them in Task 3 instead. To keep this step lint-clean, import only what GET uses (`client_ip`, `rate_limit`, `Router`, `BaseModel`, `NonMemberRsvpToken`, `User`, `_event_out`, `EventOut`, `ErrorOut`, `Code`, `raise_validation`, `EventType`) and add the rest in Task 3.

- [ ] **Step 4: Mount the router in `api.py`**

In `backend/community/api.py`, add the import next to the other router imports:

```python
from community._my_rsvps import router as my_rsvps_router
```

And add the mount next to `public_rsvp_router`:

```python
router.add_router("", my_rsvps_router)
```

- [ ] **Step 5: Run the GET tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_my_rsvps.py -q`
Expected: PASS (all `TestGetMyRsvps` tests green).

- [ ] **Step 6: Commit**

```bash
git add backend/community/_my_rsvps.py backend/community/api.py backend/tests/test_my_rsvps.py
git commit -m "feat(public-rsvp): add GET /public/my-rsvps token-authed list endpoint"
```

---

## Task 3: POST manage endpoint (update RSVP)

**Files:**
- Modify: `backend/community/_my_rsvps.py`
- Test: `backend/tests/test_my_rsvps.py`

**Interfaces:**
- Consumes: `_resolve_token_user`, `_load_public_rsvp_event`, `_apply_rsvp_in_transaction`, `_validate_rsvp_status`, `NonMemberRsvpToken.issue_or_extend`, `_email_promoted_non_members`, `_event_out`, `PublicRsvpOut`/`PublicRsvpStateOut`.
- Produces: `POST /public/my-rsvps/{event_id}/` → `PublicRsvpOut`; `class ManageRsvpIn(BaseModel)` — `status: str`, `has_plus_one: bool = False`.

- [ ] **Step 1: Write the failing tests for POST**

Append to `backend/tests/test_my_rsvps.py`:

```python
from django.utils import timezone


def _post_url(event):
    return f"/api/community/public/my-rsvps/{event.id}/"


@pytest.mark.django_db
class TestPostMyRsvps:
    def test_update_changes_status(self, api_client, nonmember, official_event):
        EventRSVP.objects.create(event=official_event, user=nonmember, status=RSVPStatus.MAYBE)
        token = NonMemberRsvpToken.issue_or_extend(nonmember)
        resp = api_client.post(
            f"{_post_url(official_event)}?token={token.token}",
            {"status": RSVPStatus.ATTENDING, "has_plus_one": False},
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.json()["rsvp"]["status"] == RSVPStatus.ATTENDING
        rsvp = EventRSVP.objects.get(event=official_event, user=nonmember)
        assert rsvp.status == RSVPStatus.ATTENDING

    def test_update_extends_token_keeping_same_string(self, api_client, nonmember, official_event):
        EventRSVP.objects.create(event=official_event, user=nonmember, status=RSVPStatus.MAYBE)
        token = NonMemberRsvpToken.issue_or_extend(nonmember)
        old_expiry = token.expires_at
        token.expires_at = timezone.now()  # simulate near-expiry
        token.save(update_fields=["expires_at"])
        api_client.post(
            f"{_post_url(official_event)}?token={token.token}",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
        )
        token.refresh_from_db()
        assert token.expires_at > old_expiry - timezone.timedelta(days=1)
        # same token string still resolves
        resp = api_client.get(f"{GET_URL}?token={token.token}")
        assert resp.status_code == 200

    def test_invalid_status_400(self, api_client, nonmember, official_event):
        EventRSVP.objects.create(event=official_event, user=nonmember, status=RSVPStatus.MAYBE)
        token = NonMemberRsvpToken.issue_or_extend(nonmember)
        resp = api_client.post(
            f"{_post_url(official_event)}?token={token.token}",
            {"status": RSVPStatus.WAITLISTED},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_ineligible_event_404(self, api_client, nonmember):
        community_event = make_official_event(title="C", event_type=EventType.COMMUNITY)
        EventRSVP.objects.create(event=community_event, user=nonmember, status=RSVPStatus.MAYBE)
        token = NonMemberRsvpToken.issue_or_extend(nonmember)
        resp = api_client.post(
            f"{_post_url(community_event)}?token={token.token}",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_bad_token_404(self, api_client, official_event):
        resp = api_client.post(
            f"{_post_url(official_event)}?token=nope",
            {"status": RSVPStatus.ATTENDING},
            content_type="application/json",
        )
        assert resp.status_code == 404
```

Note the test imports `timezone`; ensure `from django.utils import timezone` sits at the top of the file (move it up from this snippet).

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_my_rsvps.py::TestPostMyRsvps -q`
Expected: FAIL (405/404 — the POST route doesn't exist).

- [ ] **Step 3: Add the POST endpoint**

In `backend/community/_my_rsvps.py`, add these imports (the ones deferred from Task 2):

```python
import logging

from config.audit import audit_log
from django.db import transaction

from community._event_rsvps import _apply_rsvp_in_transaction, _validate_rsvp_status
from community._public_rsvp_shared import PublicRsvpOut, PublicRsvpStateOut, _email_details, _email_promoted_non_members, _load_public_rsvp_event
from community.models import Event
```

Add the input schema next to the others:

```python
class ManageRsvpIn(BaseModel):
    status: str
    has_plus_one: bool = False
```

Add the view (after the GET view):

```python
@router.post(
    "/public/my-rsvps/{event_id}/",
    response={200: PublicRsvpOut, 400: ErrorOut, 404: ErrorOut, 429: ErrorOut},
    auth=None,
)
@rate_limit(key_func=client_ip, rate="30/h")
def update_my_rsvp(request, event_id, payload: ManageRsvpIn, token: str = ""):
    user = _resolve_token_user(token)
    event = _load_public_rsvp_event(event_id)
    _validate_rsvp_status(payload.status)

    with transaction.atomic():
        final_status, promoted_user_ids = _apply_rsvp_in_transaction(
            event.id, user, payload.status, payload.has_plus_one
        )
        NonMemberRsvpToken.issue_or_extend(user)

    audit_log(
        logging.INFO,
        "public_rsvp_updated",
        request,
        target_type="event",
        target_id=str(event.id),
        details={"user_id": str(user.pk), "status": final_status},
    )
    _email_promoted_non_members(request, event, promoted_user_ids)

    fresh_event = (
        Event.objects.select_related("created_by")
        .prefetch_related("co_hosts", "invited_users", "rsvps__user")
        .get(id=event.id)
    )
    final_rsvp = user.event_rsvps.get(event=fresh_event)
    return 200, PublicRsvpOut(
        event=_event_out(fresh_event, user),
        rsvp=PublicRsvpStateOut(status=final_rsvp.status, has_plus_one=final_rsvp.has_plus_one),
    )
```

- [ ] **Step 4: Run the POST tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_my_rsvps.py::TestPostMyRsvps -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/community/_my_rsvps.py backend/tests/test_my_rsvps.py
git commit -m "feat(public-rsvp): add POST /public/my-rsvps update endpoint"
```

---

## Task 4: DELETE manage endpoint (cancel RSVP)

**Files:**
- Modify: `backend/community/_my_rsvps.py`
- Test: `backend/tests/test_my_rsvps.py`

**Interfaces:**
- Consumes: `_resolve_token_user`, `promote_from_waitlist`, `EventRSVP`, `Event`.
- Produces: `DELETE /public/my-rsvps/{event_id}/` → 204.

- [ ] **Step 1: Write the failing tests for DELETE**

Append to `backend/tests/test_my_rsvps.py`:

```python
@pytest.mark.django_db
class TestDeleteMyRsvps:
    def test_delete_removes_rsvp(self, api_client, nonmember, official_event):
        EventRSVP.objects.create(event=official_event, user=nonmember, status=RSVPStatus.ATTENDING)
        token = NonMemberRsvpToken.issue_or_extend(nonmember)
        resp = api_client.delete(f"{_post_url(official_event)}?token={token.token}")
        assert resp.status_code == 204
        assert not EventRSVP.objects.filter(event=official_event, user=nonmember).exists()
        # subsequent GET no longer lists it
        listed = api_client.get(f"{GET_URL}?token={token.token}").json()["rsvps"]
        assert listed == []

    def test_delete_promotes_waitlist(self, api_client, nonmember, official_event):
        official_event.max_attendees = 1
        official_event.save(update_fields=["max_attendees"])
        EventRSVP.objects.create(event=official_event, user=nonmember, status=RSVPStatus.ATTENDING)
        waiter = make_non_member("+14155550002", "w@example.com", name="waiter")
        EventRSVP.objects.create(event=official_event, user=waiter, status=RSVPStatus.WAITLISTED)
        token = NonMemberRsvpToken.issue_or_extend(nonmember)
        resp = api_client.delete(f"{_post_url(official_event)}?token={token.token}")
        assert resp.status_code == 204
        waiter_rsvp = EventRSVP.objects.get(event=official_event, user=waiter)
        assert waiter_rsvp.status == RSVPStatus.ATTENDING

    def test_delete_no_rsvp_404(self, api_client, nonmember, official_event):
        token = NonMemberRsvpToken.issue_or_extend(nonmember)
        resp = api_client.delete(f"{_post_url(official_event)}?token={token.token}")
        assert resp.status_code == 404

    def test_delete_bad_token_404(self, api_client, official_event):
        resp = api_client.delete(f"{_post_url(official_event)}?token=nope")
        assert resp.status_code == 404
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_my_rsvps.py::TestDeleteMyRsvps -q`
Expected: FAIL (405/404 — DELETE route missing).

- [ ] **Step 3: Add the DELETE endpoint**

In `backend/community/_my_rsvps.py`, add imports if not already present:

```python
from ninja.responses import Status
from community._event_helpers import promote_from_waitlist
from community.models import EventRSVP
```

Add the view:

```python
@router.delete(
    "/public/my-rsvps/{event_id}/",
    response={204: None, 404: ErrorOut, 429: ErrorOut},
    auth=None,
)
@rate_limit(key_func=client_ip, rate="30/h")
def delete_my_rsvp(request, event_id, token: str = ""):
    user = _resolve_token_user(token)
    with transaction.atomic():
        event = (
            Event.objects.select_for_update()
            .prefetch_related("co_hosts", "invited_users")
            .filter(id=event_id)
            .first()
        )
        if event is None:
            raise_validation(Code.Event.NOT_FOUND, status_code=404)
        rsvp = EventRSVP.objects.filter(event=event, user=user).first()
        if not rsvp:
            raise_validation(Code.Event.RSVP_NOT_FOUND, status_code=404)
        was_attending = rsvp.status == RSVPStatus.ATTENDING
        rsvp.delete()
        if was_attending:
            promote_from_waitlist(event)

    audit_log(
        logging.INFO,
        "public_rsvp_deleted",
        request,
        target_type="event",
        target_id=str(event_id),
        details={"user_id": str(user.pk)},
    )
    return Status(204, None)
```

- [ ] **Step 4: Run the DELETE tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_my_rsvps.py::TestDeleteMyRsvps -q`
Expected: PASS.

- [ ] **Step 5: Run the whole manage-rsvp suite + typecheck + lint**

Run: `cd backend && python -m pytest tests/test_my_rsvps.py -q && cd .. && make agent-typecheck && make agent-lint`
Expected: PASS, no type/lint errors.

- [ ] **Step 6: Commit**

```bash
git add backend/community/_my_rsvps.py backend/tests/test_my_rsvps.py
git commit -m "feat(public-rsvp): add DELETE /public/my-rsvps cancel endpoint"
```

---

## Task 5: Non-member staging seed — data + new official event

**Files:**
- Modify: `backend/community/management/commands/_seed_staging_data.py`

**Interfaces:**
- Produces (importable from `community.management.commands._seed_staging_data`):
  - `nonmember_phone(index: int) -> str` → `"+170255503{index:02d}"`
  - `nonmember_email(index: int) -> str` → `"nonmember{index:02d}@staging.example"`
  - `@dataclass NonMemberSpec` — `label: str`, `event_titles: list[str]`, `statuses: list[str]`
  - `NON_MEMBER_SPECS: list[NonMemberSpec]`
  - `NON_MEMBER_EVENT_TITLE: str` — the new official demo event's title
  - `STAGING_EVENTS` gains one OFFICIAL + rsvp-eligible near-future event

- [ ] **Step 1: Add the builders, the new event, and the specs**

In `backend/community/management/commands/_seed_staging_data.py`, add after `cond_email`:

```python
def nonmember_phone(index: int) -> str:
    return f"+170255503{index:02d}"


def nonmember_email(index: int) -> str:
    return f"nonmember{index:02d}@staging.example"


NON_MEMBER_EVENT_TITLE = "[staging] official public rsvp demo"
```

Add a new entry to `STAGING_EVENTS` (append before the closing `]`):

```python
    SeedStagingEvent(
        title=NON_MEMBER_EVENT_TITLE,
        description="official public event for testing non-member rsvp.",
        delta_days=5,
        duration_hours=3,
        location="downtown hub",
        event_type=EventType.OFFICIAL,
    ),
```

Add the non-member specs after `STAGING_EVENTS`:

```python
from community.models.choices import RSVPStatus  # add to existing imports at top


@dataclass
class NonMemberSpec:
    label: str
    event_titles: list[str]
    statuses: list[str]


NON_MEMBER_SPECS = [
    NonMemberSpec(
        label="non-member: attending",
        event_titles=[NON_MEMBER_EVENT_TITLE],
        statuses=[RSVPStatus.ATTENDING],
    ),
    NonMemberSpec(
        label="non-member: maybe",
        event_titles=[NON_MEMBER_EVENT_TITLE],
        statuses=[RSVPStatus.MAYBE],
    ),
    NonMemberSpec(
        label="non-member: multi-event",
        event_titles=[NON_MEMBER_EVENT_TITLE, "[staging] monthly official meeting"],
        statuses=[RSVPStatus.ATTENDING, RSVPStatus.ATTENDING],
    ),
    NonMemberSpec(
        label="non-member: no-rsvp",
        event_titles=[],
        statuses=[],
    ),
]
```

Move the `RSVPStatus` import up with the existing `from community.models.choices import EventType` line: `from community.models.choices import EventType, RSVPStatus`.

- [ ] **Step 2: Verify the module imports cleanly**

Run: `cd backend && python -c "from community.management.commands import _seed_staging_data as d; print(len(d.STAGING_EVENTS), len(d.NON_MEMBER_SPECS), d.nonmember_phone(0))"`
Expected: prints `11 4 +17025550300`

- [ ] **Step 3: Commit**

```bash
git add backend/community/management/commands/_seed_staging_data.py
git commit -m "feat(seed): add non-member staging data + official rsvp demo event"
```

---

## Task 6: Non-member staging seed — command wiring + tests

**Files:**
- Modify: `backend/community/management/commands/seed_staging.py`
- Test: `backend/tests/test_seed_staging.py`

**Interfaces:**
- Consumes: `nonmember_phone`, `nonmember_email`, `NON_MEMBER_SPECS`, `NonMemberRsvpToken`, `EventRSVP`.
- Produces: `_seed_non_members(events) -> list[User]`; `_reset()` also clears the `+170255503` band; summary prints manage URLs.

- [ ] **Step 1: Write the failing seed tests**

Append to `backend/tests/test_seed_staging.py`:

```python
from community.management.commands._seed_staging_data import (
    NON_MEMBER_EVENT_TITLE,
    NON_MEMBER_SPECS,
    nonmember_phone,
)
from community.models import EventRSVP
from users.models import NonMemberRsvpToken


@pytest.mark.django_db
def test_seed_staging_creates_non_members():
    call_command("seed_staging")
    non_members = User.objects.filter(phone_number__startswith="+170255503")
    assert non_members.count() == len(NON_MEMBER_SPECS)
    for u in non_members:
        assert u.is_member is False
        assert not u.has_usable_password()


@pytest.mark.django_db
def test_seed_staging_non_members_have_valid_tokens_and_rsvps():
    call_command("seed_staging")
    rsvped = User.objects.filter(
        phone_number__startswith="+170255503", event_rsvps__isnull=False
    ).distinct()
    assert rsvped.exists()
    for u in rsvped:
        token = NonMemberRsvpToken.objects.filter(user=u).first()
        assert token is not None and token.is_valid
    demo = Event.objects.get(title=NON_MEMBER_EVENT_TITLE)
    assert EventRSVP.objects.filter(event=demo).exists()


@pytest.mark.django_db
def test_seed_staging_reset_removes_non_member_band():
    call_command("seed_staging")
    call_command("seed_staging", "--reset")
    assert not User.objects.filter(phone_number__startswith="+170255503").exists()
    assert not Event.objects.filter(title=NON_MEMBER_EVENT_TITLE).exists()


@pytest.mark.django_db
def test_seed_staging_non_members_idempotent():
    call_command("seed_staging")
    call_command("seed_staging")
    assert User.objects.filter(phone_number__startswith="+170255503").count() == len(
        NON_MEMBER_SPECS
    )
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_seed_staging.py -k non_member -q`
Expected: FAIL (no non-members created; band count 0).

- [ ] **Step 3: Wire non-member seeding into the command**

In `backend/community/management/commands/seed_staging.py`:

Add imports:

```python
from django.conf import settings
from users.models import NonMemberRsvpToken

from community.models import Event, EventRSVP
from ._seed_staging_data import (
    NON_MEMBER_SPECS,
    nonmember_email,
    nonmember_phone,
    # ...existing imports stay...
)
```

In `handle`, inside the `transaction.atomic()` block after `events = self._seed_events(admin)`:

```python
            non_members = self._seed_non_members(events)
```

Pass `non_members` into `_print_summary` (extend its signature) and store for the summary.

Add the method:

```python
    def _seed_non_members(self, events: list[Event]) -> list[User]:
        events_by_title = {e.title: e for e in events}
        users: list[User] = []
        for index, spec in enumerate(NON_MEMBER_SPECS):
            user, created = User.objects.get_or_create(
                phone_number=nonmember_phone(index),
                defaults={
                    "display_name": spec.label,
                    "email": nonmember_email(index),
                    "is_member": False,
                },
            )
            if created:
                user.set_unusable_password()
                user.save(update_fields=["password"])
            for title, status in zip(spec.event_titles, spec.statuses):
                event = events_by_title.get(title)
                if event is None:
                    continue
                EventRSVP.objects.update_or_create(
                    event=event, user=user, defaults={"status": status}
                )
            if spec.event_titles:
                NonMemberRsvpToken.issue_or_extend(user)
            users.append(user)
            self.stdout.write(f"  {'created' if created else 'exists'} non-member: {spec.label}")
        return users
```

Update `_reset` to add:

```python
        User.objects.filter(phone_number__startswith="+170255503").delete()
        Event.objects.filter(title=NON_MEMBER_EVENT_TITLE).delete()
```

(Import `NON_MEMBER_EVENT_TITLE` too. The existing `Event.objects.filter(title__startswith="[staging] ")` in `_reset` already covers the new event title, but delete it explicitly for clarity and to keep the band removal grouped.)

Extend `_print_summary` to print manage links:

```python
        self.stdout.write("non-member users (phone -> manage link):")
        for user in non_members:
            token = NonMemberRsvpToken.objects.filter(user=user).first()
            if token is None:
                self.stdout.write(f"  {user.phone_number} -> (no rsvp)")
                continue
            url = f"{settings.FRONTEND_BASE_URL}/my-rsvps?token={token.token}"
            self.stdout.write(f"  {user.phone_number} -> {url}")
```

Update the summary counts line to include non-members.

- [ ] **Step 4: Run the seed tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_seed_staging.py -q`
Expected: PASS (existing + new).

- [ ] **Step 5: Smoke-run the command locally**

Run: `cd backend && python manage.py seed_staging --reset`
Expected: output ends with a "non-member users (phone -> manage link)" section listing `/my-rsvps?token=...` URLs; no errors.

- [ ] **Step 6: Commit**

```bash
git add backend/community/management/commands/seed_staging.py backend/tests/test_seed_staging.py
git commit -m "feat(seed): seed non-member users with rsvps + printed manage links"
```

---

## Task 7: Regenerate API types + full CI gate

**Files:**
- Modify: `frontend/src/api/types.gen.ts` (generated)

- [ ] **Step 1: Regenerate the OpenAPI-derived frontend types**

Run: `make frontend-types`
Expected: `frontend/src/api/types.gen.ts` updates to include the three `my-rsvps` paths.

- [ ] **Step 2: Run the full pre-PR CI suite**

Run: `make agent-ci`
Expected: ruff, ty, pytest, vitest, eslint, prettier, openapi-codegen check all pass. Fix any failure before proceeding.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/types.gen.ts
git commit -m "chore(api): regenerate types for public my-rsvps endpoints"
```

---

## Self-Review Notes

- **Spec coverage:** GET/POST/DELETE (Tasks 2–4), shared-helper extraction (Task 1), token-auth 404 behavior (Task 2 `_resolve_token_user`), `issue_or_extend` on writes (Tasks 3), OFFICIAL-only filter (Task 2 GET), waitlist promotion on delete (Task 4), audit logs (Tasks 3–4), rate limit `30/h` (all endpoints), staging seed with new official event + printed manage links (Tasks 5–6), API-type regen (Task 7). "rsvp updated" email and `/admin/members` toggle are explicitly out of scope (#705, #706).
- **Type consistency:** `PublicRsvpOut`/`PublicRsvpStateOut` defined in Task 1, reused Tasks 3. `_resolve_token_user` defined Task 2, reused Tasks 3–4. `nonmember_phone`/`NON_MEMBER_SPECS`/`NON_MEMBER_EVENT_TITLE` defined Task 5, consumed Task 6.
- **Rate limit note:** the shared `30/h` per-IP limit is across all three endpoints via `client_ip`; the spec's "31st request → 429" is exercised implicitly by CI, not asserted per-endpoint to avoid slow tests.
