import importlib

from django.db import migrations

# Catches users whose flags changed between the first backfill and the dual-write deploy.
backfill = importlib.import_module("users.migrations.0059_backfill_membership_status")


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0059_backfill_membership_status"),
    ]

    operations = [
        migrations.RunPython(backfill.backfill_membership_status, migrations.RunPython.noop),
    ]
