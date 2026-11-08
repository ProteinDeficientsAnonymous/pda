from django.db import migrations, models

RATING, STARS = "rating", "stars"


def _rating_to_stars(apps, _schema_editor):
    question = apps.get_model("community", "SurveyQuestion")
    question.objects.filter(field_type=RATING).update(field_type=STARS)


def _stars_to_rating(apps, _schema_editor):
    question = apps.get_model("community", "SurveyQuestion")
    question.objects.filter(field_type=STARS).update(field_type=RATING)


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0118_joinrequest_phone_number_index"),
    ]

    operations = [
        migrations.AlterField(
            model_name="surveyquestion",
            name="field_type",
            field=models.CharField(
                choices=[
                    ("text", "Text"),
                    ("textarea", "Text area"),
                    ("radio", "Radio"),
                    ("select", "Select"),
                    ("checkbox", "Checkbox"),
                    ("number", "Number"),
                    ("boolean", "Yes / No"),
                    ("stars", "Stars"),
                    ("datetime_poll", "Datetime poll"),
                    ("section", "Section"),
                ],
                default="text",
                max_length=20,
            ),
        ),
        migrations.RunPython(_rating_to_stars, _stars_to_rating),
    ]
