from django.db import migrations, models

CHOICES = [
    ("public_rsvper", "public rsvper"),
    ("tentative", "tentative"),
    ("active_member", "active member"),
    ("attendance_paused", "attendance paused"),
    ("archived", "archived"),
    ("guidelines_paused", "guidelines paused"),
]


def move_rejected_to_base(apps, schema_editor):
    User = apps.get_model("users", "User")
    User.objects.filter(membership_status="rejected").update(membership_status="public_rsvper")


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0065_remove_user_is_member"),
    ]

    # Rejection lives on the join request now; the reverse can't tell who was rejected.
    operations = [
        migrations.RunPython(move_rejected_to_base, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="user",
            name="membership_status",
            field=models.CharField(
                choices=CHOICES, db_index=True, default="public_rsvper", max_length=20
            ),
        ),
    ]
