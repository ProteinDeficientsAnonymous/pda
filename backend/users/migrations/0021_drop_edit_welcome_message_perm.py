"""Drop the retired edit_welcome_message permission key from Role.permissions.

The welcome-template editor is now gated on approve_join_requests instead, so
edit_welcome_message is dead. Role.permissions is a JSONField holding raw
strings, so old values would survive even without this — they'd just be
ignored at runtime. Scrub them anyway for tidiness and to keep the role
editor's permission grid aligned with the truth.
"""

from django.db import migrations

DOOMED_KEY = "edit_welcome_message"


def drop_key(apps, schema_editor):
    Role = apps.get_model("users", "Role")
    for role in Role.objects.all():
        perms = role.permissions or []
        if DOOMED_KEY in perms:
            role.permissions = [p for p in perms if p != DOOMED_KEY]
            role.save(update_fields=["permissions"])


def restore_key(apps, schema_editor):
    # No-op: we don't know which roles previously held the key, so we can't
    # faithfully restore it. The forward migration is destructive but harmless
    # given the key's runtime no-op status.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0020_user_onboarded_at"),
    ]

    operations = [
        migrations.RunPython(drop_key, reverse_code=restore_key),
    ]
