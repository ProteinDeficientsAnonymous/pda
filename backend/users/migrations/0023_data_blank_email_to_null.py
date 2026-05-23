from django.db import migrations


def blanks_to_null(apps, schema_editor):
    User = apps.get_model("users", "User")
    User.objects.filter(email="").update(email=None)


def null_to_blanks(apps, schema_editor):
    User = apps.get_model("users", "User")
    User.objects.filter(email__isnull=True).update(email="")


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0022_user_email_nullable"),
    ]

    operations = [
        migrations.RunPython(blanks_to_null, null_to_blanks),
    ]
