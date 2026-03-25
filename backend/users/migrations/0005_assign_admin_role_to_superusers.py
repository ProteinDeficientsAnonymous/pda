from django.db import migrations


def assign_admin_role_to_superusers(apps, schema_editor):
    User = apps.get_model("users", "User")
    Role = apps.get_model("users", "Role")
    try:
        admin_role = Role.objects.get(name="admin", is_default=True)
    except Role.DoesNotExist:
        return
    for user in User.objects.filter(is_superuser=True):
        user.roles.add(admin_role)


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0004_add_roles_m2m_to_user"),
    ]

    operations = [
        migrations.RunPython(
            assign_admin_role_to_superusers,
            migrations.RunPython.noop,
        ),
    ]
