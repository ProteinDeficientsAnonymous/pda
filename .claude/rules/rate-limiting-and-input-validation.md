---
paths:
  - "**/api.py"
  - "**/_*.py"
  - "**/schemas.py"
---

# Rate Limiting and Input Validation

## Rate Limiting (Backend)

Any endpoint that can be triggered by user action — form submissions, RSVP toggles, feedback, join requests, login attempts, poll votes — **must** use the `rate_limit` decorator from `config/ratelimit.py`.

### Usage

```python
from config.ratelimit import rate_limit

@router.post("/feedback/", auth=JWTAuth(), response={201: MessageOut, 429: ErrorOut})
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="5/m")
def submit_feedback(request, data: FeedbackIn):
    ...
```

### Key functions

| Scenario | key_func |
|----------|----------|
| Authenticated user | `lambda r: str(r.auth.pk)` |
| Unauthenticated (public form) | `lambda r: r.META.get("REMOTE_ADDR", "anon")` |
| Per-resource (e.g. per-event RSVP) | `lambda r: f"{r.auth.pk}:{resource_id}"` — capture `resource_id` in a closure |

### Suggested limits

| Endpoint type | Rate |
|---------------|------|
| Auth (login, password reset) | `5/m` |
| Public form submission (join request) | `3/h` |
| Authenticated write (RSVP, feedback, poll vote) | `10/m` |
| Admin-only mutations | no limit needed |

These are starting points — adjust based on expected usage. When in doubt, be conservative.

### Decorator order

`@rate_limit` must go **below** the `@router.*` decorator and **above** any permission helpers:

```python
@router.post("/vote/", auth=JWTAuth(), ...)
@rate_limit(key_func=lambda r: str(r.auth.pk), rate="10/m")
def cast_vote(request, data: VoteIn):
    ...
```



### Backend schema enforcement

Django model `max_length` enforces at the DB level, but Pydantic/Ninja schemas don't apply it automatically. For fields where oversized input is a real risk (public-facing endpoints), add a `max_length` constraint to the input schema:

```python
from pydantic import Field

class FeedbackIn(Schema):
    body: str = Field(..., max_length=2000)
```

This returns a 422 if the constraint is violated, before any business logic runs.
