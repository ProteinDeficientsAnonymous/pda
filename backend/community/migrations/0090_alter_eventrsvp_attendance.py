from django.db import migrations, models


def forwards(apps, schema_editor):
    EventRSVP = apps.get_model("community", "EventRSVP")
    EventRSVP.objects.filter(attendance="no_show").update(attendance="didnt_go")


def backwards(apps, schema_editor):
    EventRSVP = apps.get_model("community", "EventRSVP")
    EventRSVP.objects.filter(attendance="didnt_go").update(attendance="no_show")


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0089_alter_event_description"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
        migrations.AlterField(
            model_name="eventrsvp",
            name="attendance",
            field=models.CharField(
                choices=[
                    ("unknown", "Unknown"),
                    ("attended", "Attended"),
                    ("didnt_go", "Didn't go"),
                ],
                default="unknown",
                max_length=20,
            ),
        ),
    ]
