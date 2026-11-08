from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0132_member_restored_email_template"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="rsvp_reminder_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
