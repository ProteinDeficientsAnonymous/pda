# Photo Uploads — Implementation Plan

Covers [#63 Profile photo upload](https://github.com/leahpeker/pda/issues/63) and [#65 Event photo uploads](https://github.com/leahpeker/pda/issues/65).

---

## Storage Strategy

Both features share the same storage backend. Solve this once before implementing either.

**Local dev:** Django's built-in `MEDIA_ROOT` / `MEDIA_URL` with `FileSystemStorage`. Served by Django dev server.

**Production (Railway):** Use [`django-storages`](https://django-storages.readthedocs.io/) with an S3-compatible provider. Recommended: **Cloudflare R2** (S3-compatible, no egress fees, generous free tier) or **AWS S3**. Railway volumes are not recommended — they don't persist across deploys by default.

### Django settings changes

```python
# settings.py

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

if IS_PRODUCTION:
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
    AWS_STORAGE_BUCKET_NAME = env("STORAGE_BUCKET_NAME")
    AWS_S3_ENDPOINT_URL = env("STORAGE_ENDPOINT_URL")       # R2 endpoint or omit for AWS
    AWS_ACCESS_KEY_ID = env("STORAGE_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env("STORAGE_SECRET_ACCESS_KEY")
    AWS_S3_CUSTOM_DOMAIN = env("STORAGE_CUSTOM_DOMAIN", default=None)  # optional CDN
    AWS_QUERYSTRING_AUTH = False  # public-read URLs
```

New env vars needed (add to `.env.example` and Railway):
```
STORAGE_BUCKET_NAME=
STORAGE_ENDPOINT_URL=
STORAGE_ACCESS_KEY_ID=
STORAGE_SECRET_ACCESS_KEY=
STORAGE_CUSTOM_DOMAIN=   # optional
```

New dependency: `django-storages[s3]` (add to `pyproject.toml`).

In local dev, add to `config/urls.py`:
```python
from django.conf import settings
from django.conf.urls.static import static

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

---

## #63 — Profile Photo

### Backend

**Model** (`users/models.py`):
```python
def _profile_photo_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower()
    return f"profile-photos/{instance.pk}.{ext}"

class User(AbstractUser):
    ...
    profile_photo = models.ImageField(
        upload_to=_profile_photo_path,
        blank=True,
        null=True,
    )
```

Using the user's UUID as the filename ensures a single photo per user (new upload silently replaces old file at the same path).

**API** (`users/api.py`):

Add a dedicated upload endpoint (separate from `PATCH /me/` to keep JSON and multipart concerns apart):

```python
from ninja import File
from ninja.files import UploadedFile

@router.post("/me/photo/", response={200: UserOut, 400: ErrorOut}, auth=JWTAuth())
def upload_profile_photo(request, photo: UploadedFile = File(...)):
    if photo.content_type not in ("image/jpeg", "image/png", "image/webp"):
        return Status(400, {"detail": "Only JPEG, PNG, and WebP images are accepted."})
    if photo.size > 5 * 1024 * 1024:  # 5 MB
        return Status(400, {"detail": "Photo must be under 5 MB."})
    user = User.objects.prefetch_related("roles").get(pk=request.auth.pk)
    user.profile_photo.save(photo.name, photo, save=True)
    return Status(200, UserOut.from_user(user))
```

**Schema** (`UserOut`): Add `profile_photo_url: str | None` field:
```python
class UserOut(BaseModel):
    ...
    profile_photo_url: str | None

    @staticmethod
    def from_user(user):
        return UserOut(
            ...
            profile_photo_url=user.profile_photo.url if user.profile_photo else None,
        )
```

**Migration:** `makemigrations users` → `migrate`.

### Frontend

**Package:** Add `image_picker` to `pubspec.yaml`. Works on web (file picker), iOS (camera/gallery), and Android.

**Auth provider** (`auth_provider.dart`): Add `uploadProfilePhoto(XFile file)` method that POSTs multipart to `/api/auth/me/photo/` via Dio:
```dart
final formData = FormData.fromMap({
  'photo': await MultipartFile.fromFile(file.path, filename: file.name),
});
await _dio.post('/api/auth/me/photo/', data: formData);
```

**User model** (`models/user.dart`): Add `profilePhotoUrl: String?` field (Freezed, nullable).

**Settings screen** (`settings_screen.dart`): Replace the "Coming soon" tooltip with a real tap handler that:
1. Opens `ImagePicker().pickImage(source: ImageSource.gallery, maxWidth: 800, imageQuality: 85)`
2. Calls `authProvider.notifier.uploadProfilePhoto(file)`
3. Shows a loading indicator during upload
4. On success: provider invalidates and rebuilds — `CircleAvatar` shows `NetworkImage(profilePhotoUrl)` instead of initials

**CircleAvatar** logic:
```dart
CircleAvatar(
  radius: 48,
  backgroundImage: user.profilePhotoUrl != null
      ? NetworkImage(user.profilePhotoUrl!)
      : null,
  child: user.profilePhotoUrl == null
      ? Text(_initials(user.displayName, user.email))
      : null,
)
```

---

## #65 — Event Cover Photo

Start with a single cover photo per event (not a gallery). Gallery can be a follow-up.

### Backend

**Model** (`community/models.py`):
```python
def _event_cover_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower()
    return f"event-covers/{instance.pk}.{ext}"

class Event(Model):
    ...
    cover_photo = models.ImageField(
        upload_to=_event_cover_path,
        blank=True,
        null=True,
    )
```

**API** (`community/api.py`):

Upload endpoint (separate from event PATCH):
```python
@router.post(
    "/events/{event_id}/photo/",
    response={200: EventOut, 403: ErrorOut, 404: ErrorOut},
    auth=JWTAuth(),
)
def upload_event_photo(request, event_id: UUID, photo: UploadedFile = File(...)):
    event = get_object_or_404(Event, pk=event_id)
    if not (event.created_by_id == request.auth.pk or
            event.co_hosts.filter(pk=request.auth.pk).exists() or
            request.auth.has_perm("community.manage_events")):
        return Status(403, {"detail": "Permission denied."})
    if photo.content_type not in ("image/jpeg", "image/png", "image/webp"):
        return Status(400, {"detail": "Only JPEG, PNG, and WebP images are accepted."})
    if photo.size > 10 * 1024 * 1024:  # 10 MB
        return Status(400, {"detail": "Photo must be under 10 MB."})
    event.cover_photo.save(photo.name, photo, save=True)
    return Status(200, _event_out(event, request.auth))
```

**Schema** (`EventOut`): Add `cover_photo_url: str | None`.

**Migration:** `makemigrations community` → `migrate`.

### Frontend

**Event detail panel** (`event_detail_panel.dart`): Show cover photo at the top of the event detail view if `event.coverPhotoUrl != null`:
```dart
if (event.coverPhotoUrl != null)
  AspectRatio(
    aspectRatio: 16 / 9,
    child: Image.network(event.coverPhotoUrl!, fit: BoxFit.cover),
  ),
```

**Event form** (`EventFormDialog` in `event_detail_panel.dart`): Add an optional photo picker field. On submit, the form returns the selected `XFile?` alongside other fields. The caller (`event_management_screen.dart`) uploads the photo in a second request after creating/updating the event.

Two-step upload flow:
1. `POST /api/community/events/` or `PATCH /api/community/events/{id}/` with JSON (existing)
2. If photo selected: `POST /api/community/events/{id}/photo/` with multipart

**Event model** (`models/event.dart`): Add `coverPhotoUrl: String?` field (Freezed, nullable).

---

## Shared Considerations

### Validation (both features)
- Accepted types: JPEG, PNG, WebP
- Profile photo size limit: 5 MB
- Event cover size limit: 10 MB
- Validate on the backend — don't trust client-side checks

### Pillow
Add `Pillow` to `pyproject.toml` — required by Django's `ImageField` for validation.

### Deletion
- Profile photo: no explicit delete needed — new upload overwrites at the same path
- Event cover: add `DELETE /api/community/events/{id}/photo/` if needed later; out of scope for initial implementation

### No resizing on upload
Keep it simple for v1 — serve the original file. Add server-side resizing (via `Pillow` or a CDN transform) as a follow-up if storage/bandwidth becomes a concern.

---

## Implementation Order

1. **Storage backend** — settings, env vars, `django-storages`, local dev media serving
2. **#63 Profile photo** — smaller scope, establishes the multipart upload pattern on both backend and frontend
3. **#65 Event cover photo** — reuses the same pattern, adds display in event views

---

## Files to Change

| File | Change |
|------|--------|
| `backend/config/settings.py` | Add `MEDIA_URL`, `MEDIA_ROOT`, S3 storages config |
| `backend/config/urls.py` | Add `static(MEDIA_URL, ...)` for local dev |
| `backend/users/models.py` | Add `profile_photo` ImageField |
| `backend/users/api.py` | Add `POST /me/photo/` endpoint; update `UserOut` |
| `backend/community/models.py` | Add `cover_photo` ImageField to Event |
| `backend/community/api.py` | Add `POST /events/{id}/photo/` endpoint; update `EventOut` |
| `backend/pyproject.toml` | Add `Pillow`, `django-storages[s3]` |
| `.env.example` | Add storage env vars |
| `frontend/pubspec.yaml` | Add `image_picker` |
| `frontend/lib/models/user.dart` | Add `profilePhotoUrl` field |
| `frontend/lib/models/event.dart` | Add `coverPhotoUrl` field |
| `frontend/lib/providers/auth_provider.dart` | Add `uploadProfilePhoto()` method |
| `frontend/lib/screens/settings_screen.dart` | Wire up photo picker and upload |
| `frontend/lib/screens/calendar/event_detail_panel.dart` | Show cover photo; add picker to form |
| `frontend/lib/screens/event_management_screen.dart` | Two-step create/upload flow |
