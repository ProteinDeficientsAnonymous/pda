from django.db import migrations


def rename_permission(apps, schema_editor):
    Role = apps.get_model("users", "Role")
    for role in Role.objects.all():
        if "manage_guidelines" in (role.permissions or []):
            role.permissions = [
                "edit_guidelines" if p == "manage_guidelines" else p for p in role.permissions
            ]
            role.save(update_fields=["permissions"])


def reverse_rename(apps, schema_editor):
    Role = apps.get_model("users", "Role")
    for role in Role.objects.all():
        if "edit_guidelines" in (role.permissions or []):
            role.permissions = [
                "manage_guidelines" if p == "edit_guidelines" else p for p in role.permissions
            ]
            role.save(update_fields=["permissions"])


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0009_profile_photo"),
    ]

    operations = [
        migrations.RunPython(rename_permission, reverse_rename),
    ]
