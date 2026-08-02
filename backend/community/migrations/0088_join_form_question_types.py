from django.db import migrations, models
from django.db.models.functions import Lower


def migrate_join_question_types(apps, schema_editor):
    JoinFormQuestion = apps.get_model("community", "JoinFormQuestion")
    JoinFormQuestion.objects.filter(field_type="select").update(field_type="dropdown")
    JoinFormQuestion.objects.annotate(label_l=Lower("label")).filter(
        field_type="text", label_l__contains="why"
    ).update(field_type="textarea")


def reverse_join_question_types(apps, schema_editor):
    JoinFormQuestion = apps.get_model("community", "JoinFormQuestion")
    JoinFormQuestion.objects.filter(field_type="dropdown").update(field_type="select")
    JoinFormQuestion.objects.filter(field_type="textarea").update(field_type="text")


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0087_alter_eventrsvp_options"),
    ]

    operations = [
        migrations.AlterField(
            model_name="joinformquestion",
            name="field_type",
            field=models.CharField(
                choices=[
                    ("text", "Text"),
                    ("textarea", "Text area"),
                    ("dropdown", "Dropdown"),
                ],
                default="text",
                max_length=10,
            ),
        ),
        migrations.RunPython(migrate_join_question_types, reverse_join_question_types),
    ]
