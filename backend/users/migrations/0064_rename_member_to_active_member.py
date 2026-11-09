from django.db import migrations, models

CHOICES = [
    ("public_rsvper", "public rsvper"),
    ("tentative", "tentative"),
    ("active_member", "active member"),
    ("attendance_paused", "attendance paused"),
    ("rejected", "rejected"),
    ("archived", "archived"),
    ("guidelines_paused", "guidelines paused"),
]


def rename_member(apps, schema_editor):
    User = apps.get_model("users", "User")
    User.objects.filter(membership_status="member").update(membership_status="active_member")


def restore_member(apps, schema_editor):
    User = apps.get_model("users", "User")
    User.objects.filter(membership_status="active_member").update(membership_status="member")


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0063_is_member_generated"),
    ]

    # The generated column's expression names the old value, so drop it around the rename.
    operations = [
        migrations.RemoveField(model_name="user", name="is_member"),
        migrations.AlterField(
            model_name="user",
            name="membership_status",
            field=models.CharField(
                choices=CHOICES, db_index=True, default="public_rsvper", max_length=20
            ),
        ),
        migrations.RunPython(rename_member, restore_member),
        migrations.AddField(
            model_name="user",
            name="is_member",
            field=models.GeneratedField(
                db_index=True,
                db_persist=True,
                expression=models.Q(
                    ("membership_status__in", ("active_member", "guidelines_paused"))
                ),
                output_field=models.BooleanField(),
            ),
        ),
    ]
