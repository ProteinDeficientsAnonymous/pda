from django.db import migrations, models

CHOICES = [
    ("none", "none"),
    ("tentative", "tentative"),
    ("active_member", "active member"),
    ("attendance_paused", "attendance paused"),
    ("archived", "archived"),
    ("guidelines_paused", "guidelines paused"),
]


def rename_public_rsvper(apps, schema_editor):
    User = apps.get_model("users", "User")
    User.objects.filter(membership_status="public_rsvper").update(membership_status="none")


def restore_public_rsvper(apps, schema_editor):
    User = apps.get_model("users", "User")
    User.objects.filter(membership_status="none").update(membership_status="public_rsvper")


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0066_drop_rejected_status"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="membership_status",
            field=models.CharField(choices=CHOICES, db_index=True, default="none", max_length=20),
        ),
        migrations.RunPython(rename_public_rsvper, restore_public_rsvper),
    ]
