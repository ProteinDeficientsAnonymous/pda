import django.db.models.functions.text
from django.db import migrations, models


def lowercase_emails(apps, schema_editor):
    User = apps.get_model("users", "User")
    for user in User.objects.exclude(email__isnull=True).exclude(email="").only("pk", "email"):
        cleaned = user.email.strip().lower()
        if cleaned != user.email:
            User.objects.filter(pk=user.pk).update(email=cleaned)


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0064_user_event_update_sent_on"),
    ]

    operations = [
        migrations.RemoveConstraint(model_name="user", name="unique_non_blank_email"),
        migrations.RunPython(lowercase_emails, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.UniqueConstraint(
                django.db.models.functions.text.Lower("email"),
                condition=models.Q(("email__isnull", False), models.Q(("email", ""), _negated=True)),
                name="unique_non_blank_email_ci",
            ),
        ),
    ]
