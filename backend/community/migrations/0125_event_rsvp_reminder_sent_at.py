from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0124_event_cohost_reminder_sent_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="rsvp_reminder_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
