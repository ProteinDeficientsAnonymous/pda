from django.db import migrations

from community.speech.seed import add_walk_mixup_note


def _add_note(apps, _schema_editor):
    add_walk_mixup_note(apps.get_model("community", "SpeechTemplate"))


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0152_perf_indexes"),
    ]

    operations = [
        migrations.RunPython(_add_note, migrations.RunPython.noop),
    ]
