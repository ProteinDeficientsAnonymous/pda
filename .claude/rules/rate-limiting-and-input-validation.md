---
paths:
  - "**/api.py"
  - "**/_*.py"
  - "**/schemas.py"
  - "**/screens/**/*.dart"
  - "**/widgets/**/*.dart"
  - "**/utils/validators.dart"
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

---

## Input Validation (Frontend)

All user-facing `TextFormField` inputs must have a `maxLength` constraint — both as a validator and as the field's `maxLength` property (which renders the character counter and enforces truncation at the OS level).

### Pattern

```dart
import 'package:pda/utils/validators.dart';

TextFormField(
  maxLength: 500,
  validator: all([required(), maxLength(500)]),
  ...
)
```

Use validators from `lib/utils/validators.dart`. Add new validators there — don't inline validation logic.

### Recommended limits

| Field type | maxLength |
|------------|-----------|
| Display name | 64 (already enforced by `displayName()` validator) |
| Short text (title, label) | 100–150 |
| Medium text (description, bio) | 500 |
| Long text (event description, doc body) | 2000 |
| URL fields | 500 |
| Phone number | 20 |

Match these to the corresponding Django model `max_length` — they must be consistent.

### Backend schema enforcement

Django model `max_length` enforces at the DB level, but Pydantic/Ninja schemas don't apply it automatically. For fields where oversized input is a real risk (public-facing endpoints), add a `max_length` constraint to the input schema:

```python
from pydantic import Field

class FeedbackIn(Schema):
    body: str = Field(..., max_length=2000)
```

This returns a 422 if the constraint is violated, before any business logic runs.
