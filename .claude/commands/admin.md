# Django Admin Configuration

Configure Django admin for Vedgy models.

## Usage

```
/admin
```

## Vedgy Models

- **User** (`users/models.py`): Custom `AbstractUser`, email-based auth, UUID PK
- **Listing** (`listings/models.py`): UUID PK, status flow: `draft → payment_submitted → active → expired/deactivated`
- **ListingPhoto** (`listings/models.py`): FK to Listing, stores filename only (max 10 per listing)

## Current Admin

Admin registrations are in:
- `backend/listings/admin.py`
- `backend/users/admin.py`

## Key Patterns

- Use `list_display` with status, dates, photo count
- Use `list_filter` on status, created_at
- Use `search_fields` on title, city, description
- Use `ListingPhotoInline` (TabularInline) for photo management
- Optimize with `select_related('user')` and `prefetch_related('photos')`

## Running Admin

```bash
make createsuperuser    # create admin user
make run                # visit http://localhost:8000/admin/
```
