from django.db import migrations, models
from django.db.models.functions import Lower


def migrate_question_types(apps, schema_editor):
    JoinFormQuestion = apps.get_model("community", "JoinFormQuestion")
    SurveyQuestion = apps.get_model("community", "SurveyQuestion")

    # Join: legacy "select" already means HTML <select>; keep it.
    # If an unmerged intermediate renamed it to "dropdown", restore HTML naming.
    JoinFormQuestion.objects.filter(field_type="dropdown").update(field_type="select")
    # Preserve the legacy UI heuristic that rendered "why" questions as multiline.
    JoinFormQuestion.objects.annotate(label_l=Lower("label")).filter(
        field_type="text", label_l__contains="why"
    ).update(field_type="textarea")

    # Survey renames must run in this order to avoid value collisions.
    SurveyQuestion.objects.filter(field_type="select").update(field_type="radio")
    SurveyQuestion.objects.filter(field_type="dropdown").update(field_type="select")
    SurveyQuestion.objects.filter(field_type="multiselect").update(field_type="checkbox")
    SurveyQuestion.objects.filter(field_type="yes_no").update(field_type="boolean")


def reverse_question_types(apps, schema_editor):
    JoinFormQuestion = apps.get_model("community", "JoinFormQuestion")
    SurveyQuestion = apps.get_model("community", "SurveyQuestion")

    SurveyQuestion.objects.filter(field_type="boolean").update(field_type="yes_no")
    SurveyQuestion.objects.filter(field_type="checkbox").update(field_type="multiselect")
    SurveyQuestion.objects.filter(field_type="select").update(field_type="dropdown")
    SurveyQuestion.objects.filter(field_type="radio").update(field_type="select")

    JoinFormQuestion.objects.filter(field_type="textarea").update(field_type="text")


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0091_eventrsvp_plus_one_attendance_and_more"),
    ]

    operations = [
        migrations.RunPython(migrate_question_types, reverse_question_types),
        migrations.AlterField(
            model_name="joinformquestion",
            name="field_type",
            field=models.CharField(
                choices=[
                    ("text", "Text"),
                    ("textarea", "Text area"),
                    ("select", "Select"),
                ],
                default="text",
                max_length=10,
            ),
        ),
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
                    ("rating", "Rating"),
                    ("datetime_poll", "Datetime poll"),
                ],
                default="text",
                max_length=20,
            ),
        ),
    ]
