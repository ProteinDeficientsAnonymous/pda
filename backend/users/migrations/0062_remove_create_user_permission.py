from django.db import migrations

REMOVED_KEY = "create_user"


def strip_removed_permission(apps, schema_editor):
    Role = apps.get_model("users", "Role")
    for role in Role.objects.all():
        if isinstance(role.permissions, list) and REMOVED_KEY in role.permissions:
            role.permissions = [p for p in role.permissions if p != REMOVED_KEY]
            role.save(update_fields=["permissions"])


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0061_remove_user_is_paused"),
    ]

    operations = [
        migrations.RunPython(strip_removed_permission, migrations.RunPython.noop),
    ]
