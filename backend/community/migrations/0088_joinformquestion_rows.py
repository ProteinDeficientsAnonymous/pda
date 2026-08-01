from django.db import migrations, models
from django.db.models.functions import Lower


def backfill_multiline_why_questions(apps, schema_editor):
    """Former FE heuristic: labels containing 'why' rendered as a 5-row textarea."""
    JoinFormQuestion = apps.get_model("community", "JoinFormQuestion")
    JoinFormQuestion.objects.annotate(label_l=Lower("label")).filter(
        field_type="text", label_l__contains="why", rows=1
    ).update(rows=5)


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0087_align_rsvp_question_types_with_surveys"),
    ]

    operations = [
        migrations.AddField(
            model_name="joinformquestion",
            name="rows",
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.RunPython(backfill_multiline_why_questions, migrations.RunPython.noop),
    ]
