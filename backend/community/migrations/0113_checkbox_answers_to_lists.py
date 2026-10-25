from django.db import migrations

CHECKBOX = "checkbox"
STORES = (
    ("SurveyResponse", "SurveyQuestion", "answers"),
    ("EventRSVP", "EventRsvpQuestion", "questionnaire_responses"),
)


def _convert(snapshots: dict, checkbox_ids: set[str], *, to_list: bool) -> bool:
    changed = False
    for qid, snap in snapshots.items():
        if qid not in checkbox_ids or not isinstance(snap, dict):
            continue
        answer = snap.get("answer")
        if to_list and isinstance(answer, str):
            snap["answer"] = [v.strip() for v in answer.split(",") if v.strip()]
            changed = True
        elif not to_list and isinstance(answer, list):
            snap["answer"] = ",".join(answer)
            changed = True
    return changed


def _migrate(apps, *, to_list: bool) -> None:
    for model_name, question_model_name, field in STORES:
        model = apps.get_model("community", model_name)
        question_model = apps.get_model("community", question_model_name)
        checkbox_ids = {
            str(pk)
            for pk in question_model.objects.filter(field_type=CHECKBOX).values_list(
                "id", flat=True
            )
        }
        changed = [
            row
            for row in model.objects.only("id", field).iterator()
            if _convert(getattr(row, field) or {}, checkbox_ids, to_list=to_list)
        ]
        model.objects.bulk_update(changed, [field], batch_size=500)


def forwards(apps, schema_editor):
    _migrate(apps, to_list=True)


def backwards(apps, schema_editor):
    _migrate(apps, to_list=False)


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0112_eventfeedbackrequest_survey_feedback_event_type_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
