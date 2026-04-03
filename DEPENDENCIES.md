# Dependency Update Tracker

Last reviewed: 2026-04-03 (Django 6.0.3 upgrade complete)

---

## Done

| Package | From | To | Notes |
|---------|------|----|-------|
| flutter_riverpod | 2.6.1 | 3.3.1 | ✅ migrated |
| riverpod_annotation | 2.6.1 | 4.0.2 | ✅ migrated |
| riverpod_generator | 2.6.5 | 4.0.3 | ✅ migrated |
| riverpod_lint | 2.6.5 | 3.1.3 | ✅ migrated |
| freezed | 3.1.0 | 3.2.5 | ✅ auto-updated with Riverpod 3 |
| Django | 5.2.12 | 6.0.3 | ✅ migrated (STATICFILES_STORAGE → STORAGES, unique_together → UniqueConstraint) |

---

## Safe to update (patch/minor, low risk)

### Python (backend)

| Package | Current | Latest | Notes |
|---------|---------|--------|-------|
| boto3 / botocore | 1.42.78 | 1.42.82 | patch |
| cryptography | 46.0.5 | 46.0.6 | patch |
| django-ninja-extra | 0.31.3 | 0.31.4 | patch |
| django-stubs | 6.0.1 | 6.0.2 | patch |
| django-stubs-ext | 6.0.1 | 6.0.2 | patch |
| pillow | 11.3.0 | 12.2.0 | major version but historically smooth |
| pygments | 2.19.2 | 2.20.0 | patch |
| ruff | 0.15.7 | 0.15.9 | patch |
| ty | 0.0.25 | 0.0.28 | patch |
| mypy | 1.19.1 | 1.20.0 | minor |

---

## Needs care (major versions — do one at a time with tests)

### Python (backend)

| Package | Current | Latest | Notes |
|---------|---------|--------|-------|
| ~~Django~~ | ~~5.2.12~~ | ~~6.0.3~~ | ~~breaking changes~~ — done, see Done section |
| gunicorn | 23.0.0 | 25.3.0 | review changelog |
| icalendar | 6.3.2 | 7.0.3 | API changes possible |
| phonenumbers | 8.13.55 | 9.0.27 | API changes possible |

### Flutter (frontend)

| Package | Current | Latest | Notes |
|---------|---------|--------|-------|
| go_router | 14.8.1 | 17.2.0 | significant API changes — plan separately |
| google_fonts | 6.3.3 | 8.0.2 | major |
| flutter_secure_storage | 9.2.4 | 10.0.0 | major |
| share_plus | 10.1.4 | 12.0.2 | major |
