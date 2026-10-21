from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0107_event_slug_alias"),
    ]

    operations = [
        migrations.AddField(
            model_name="eventrsvp",
            name="pre_cancel_status",
            field=models.CharField(
                blank=True,
                choices=[
                    ("attending", "Attending"),
                    ("maybe", "Maybe"),
                    ("cant_go", "Can't go"),
                    ("waitlisted", "Waitlisted"),
                    ("removed", "Removed"),
                ],
                max_length=20,
                null=True,
            ),
        ),
    ]
