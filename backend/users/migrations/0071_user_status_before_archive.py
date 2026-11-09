from django.db import migrations, models

CHOICES = [
    ("none", "none"),
    ("tentative", "tentative"),
    ("active_member", "active member"),
    ("attendance_paused", "attendance paused"),
    ("archived", "archived"),
    ("guidelines_paused", "guidelines paused"),
]


def backfill_status_before_archive(apps, schema_editor):
    User = apps.get_model("users", "User")
    # Re-evaluated per update, so each step only fills rows the earlier ones left null.
    unset = User.objects.filter(membership_status="archived", status_before_archive__isnull=True)
    unset.filter(is_paused=True).update(status_before_archive="guidelines_paused")
    unset.filter(attendance_paused_at__isnull=False).update(
        status_before_archive="attendance_paused"
    )
    members = unset.filter(roles__name="member", roles__is_default=True).values_list(
        "pk", flat=True
    )
    User.objects.filter(pk__in=list(members)).update(status_before_archive="active_member")
    unset.update(status_before_archive="none")


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0070_remove_user_archived_by"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="status_before_archive",
            field=models.CharField(blank=True, choices=CHOICES, max_length=20, null=True),
        ),
        migrations.RunPython(backfill_status_before_archive, migrations.RunPython.noop),
    ]
