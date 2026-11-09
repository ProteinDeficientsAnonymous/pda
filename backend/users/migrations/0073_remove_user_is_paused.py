from django.db import migrations
from django.db.models import Q


def restore_pause_flag(apps, schema_editor):
    User = apps.get_model("users", "User")
    User.objects.filter(
        Q(membership_status="guidelines_paused")
        | Q(membership_status="archived", status_before_archive="guidelines_paused")
    ).update(is_paused=True)


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0072_move_pause_flag_to_status"),
    ]

    operations = [
        # Reverse runs after the column is re-added, so a rollback keeps every pause.
        migrations.RunPython(migrations.RunPython.noop, restore_pause_flag),
        migrations.RemoveField(model_name="user", name="is_paused"),
    ]
