from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0089_alter_event_description"),
    ]

    operations = [
        migrations.AddField(
            model_name="eventrsvp",
            name="previous_status",
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
