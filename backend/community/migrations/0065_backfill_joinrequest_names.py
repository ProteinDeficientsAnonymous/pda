from django.db import migrations
from users._name_parsing import parse_display_name


def backfill(apps, schema_editor):
    JoinRequest = apps.get_model("community", "JoinRequest")
    for join_request in JoinRequest.objects.all().iterator():
        first, last = parse_display_name(join_request.display_name or "")
        join_request.first_name = first
        join_request.last_name = last
        join_request.save(update_fields=["first_name", "last_name"])


def noop_reverse(apps, schema_editor):
    # display_name is untouched, so reversing just leaves the parsed columns.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0064_joinrequest_first_name_joinrequest_last_name"),
    ]
    operations = [migrations.RunPython(backfill, noop_reverse)]
