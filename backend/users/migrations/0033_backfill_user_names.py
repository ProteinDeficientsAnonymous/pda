from django.db import migrations

from users._name_parsing import parse_display_name


def backfill(apps, schema_editor):
    User = apps.get_model("users", "User")
    for user in User.objects.all().iterator():
        first, last = parse_display_name(user.display_name or "")
        user.first_name = first
        user.last_name = last
        user.save(update_fields=["first_name", "last_name"])


def noop_reverse(apps, schema_editor):
    # display_name is untouched, so reversing just leaves the parsed columns.
    pass


class Migration(migrations.Migration):
    dependencies = [("users", "0032_user_first_last_name")]
    operations = [migrations.RunPython(backfill, noop_reverse)]
