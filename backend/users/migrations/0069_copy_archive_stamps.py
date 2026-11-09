from django.db import migrations
from django.db.models import F


def copy_archive_stamps(apps, schema_editor):
    User = apps.get_model("users", "User")
    User.objects.filter(membership_status="archived").update(
        membership_status_changed_at=F("archived_at"),
        membership_status_changed_by_id=F("archived_by_id"),
    )


def restore_archived_by(apps, schema_editor):
    User = apps.get_model("users", "User")
    User.objects.filter(membership_status="archived").update(
        archived_by_id=F("membership_status_changed_by_id")
    )


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0068_user_membership_status_changed"),
    ]

    operations = [
        migrations.RunPython(copy_archive_stamps, restore_archived_by),
    ]
