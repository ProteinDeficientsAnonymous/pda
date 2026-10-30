from django.db import migrations

STARS = "stars"


def _clear_star_labels(apps, _schema_editor):
    question = apps.get_model("community", "SurveyQuestion")
    question.objects.filter(field_type=STARS).update(options=[])


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0120_scale_question_type"),
    ]

    operations = [
        migrations.RunPython(_clear_star_labels, migrations.RunPython.noop),
    ]
