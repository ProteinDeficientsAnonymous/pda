from django.db import migrations

from users.models import normalize_phone_number


def normalize_existing_phone_numbers(apps, schema_editor):
    User = apps.get_model("users", "User")
    for user in User.objects.all():
        canonical = normalize_phone_number(user.phone_number)
        if canonical != user.phone_number:
            user.phone_number = canonical
            user.save(update_fields=["phone_number"])


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0041_user_contact_privacy_consent_at"),
    ]

    operations = [
        migrations.RunPython(normalize_existing_phone_numbers, migrations.RunPython.noop),
    ]
