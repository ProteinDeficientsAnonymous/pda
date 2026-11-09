from django.db import migrations
from django.utils import timezone


def move_pause_flag_to_status(apps, schema_editor):
    User = apps.get_model("users", "User")
    paused = User.objects.filter(is_paused=True)
    paused.filter(membership_status="archived").update(status_before_archive="guidelines_paused")
    # Fails closed: a stray paused tentative or none row stays blocked once reads use the status.
    paused.exclude(membership_status__in=("guidelines_paused", "archived")).update(
        membership_status="guidelines_paused",
        attendance_paused_at=None,
        membership_status_changed_at=timezone.now(),
        membership_status_changed_by=None,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0071_user_status_before_archive"),
    ]

    operations = [
        migrations.RunPython(move_pause_flag_to_status, migrations.RunPython.noop),
    ]
