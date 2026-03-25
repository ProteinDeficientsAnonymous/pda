# Django Model Generator

Create Django models following Vedgy conventions.

## Usage

```
/django-model
```

## Vedgy Conventions

- **UUID primary keys** on all models (`id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)`)
- **Timestamps**: `created_at = DateTimeField(auto_now_add=True)`, `updated_at = DateTimeField(auto_now=True)`
- **Status fields**: use `TextChoices` enum classes
- **ForeignKey to User**: `from users.models import User`, use `on_delete=models.CASCADE`
- Models live in `backend/listings/models.py` or `backend/users/models.py`

## After Creating Models

```bash
make migrate    # makemigrations + migrate
```

## Existing Models

- **User** (`users/models.py`): `AbstractUser`, email as `USERNAME_FIELD`, UUID PK
- **Listing** (`listings/models.py`): housing listing with status flow, auto-expire after 30 days
- **ListingPhoto** (`listings/models.py`): FK to Listing, filename-only storage (photos in B2/local)
