from django.db import migrations

from community.speech.seed import seed_default_template


def _seed(apps, _schema_editor):
    seed_default_template(apps.get_model("community", "SpeechTemplate"))


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0127_eventspeech"),
    ]

    operations = [
        migrations.RunPython(_seed, migrations.RunPython.noop),
    ]
