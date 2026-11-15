from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0138_eventrsvp_no_show_emailed_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="rsvp_reminder_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
