import uuid as _uuid

from django.db import migrations

# Fixed UUIDs so the migration is deterministic and reversible.
WHY_JOIN_UUID = _uuid.UUID("a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d")
HOW_HEARD_UUID = _uuid.UUID("b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e")


def seed_questions_and_migrate_answers(apps, schema_editor):
    JoinFormQuestion = apps.get_model("community", "JoinFormQuestion")
    JoinRequest = apps.get_model("community", "JoinRequest")

    # Create default questions
    JoinFormQuestion.objects.get_or_create(
        id=WHY_JOIN_UUID,
        defaults={
            "label": "Why do you want to join?",
            "field_type": "text",
            "required": True,
            "display_order": 0,
        },
    )
    JoinFormQuestion.objects.get_or_create(
        id=HOW_HEARD_UUID,
        defaults={
            "label": "How did you hear about us?",
            "field_type": "text",
            "required": False,
            "display_order": 1,
        },
    )

    # Migrate existing answers
    for jr in JoinRequest.objects.all():
        answers = {}
        if jr.why_join:
            answers[str(WHY_JOIN_UUID)] = {
                "label": "Why do you want to join?",
                "answer": jr.why_join,
            }
        if jr.how_they_heard:
            answers[str(HOW_HEARD_UUID)] = {
                "label": "How did you hear about us?",
                "answer": jr.how_they_heard,
            }
        if answers:
            jr.custom_answers = answers
            jr.save(update_fields=["custom_answers"])


def reverse_migrate(apps, schema_editor):
    JoinFormQuestion = apps.get_model("community", "JoinFormQuestion")
    JoinRequest = apps.get_model("community", "JoinRequest")

    for jr in JoinRequest.objects.all():
        why_data = jr.custom_answers.get(str(WHY_JOIN_UUID), {})
        how_data = jr.custom_answers.get(str(HOW_HEARD_UUID), {})
        jr.why_join = why_data.get("answer", "")
        jr.how_they_heard = how_data.get("answer", "")
        jr.save(update_fields=["why_join", "how_they_heard"])

    JoinFormQuestion.objects.filter(id__in=[WHY_JOIN_UUID, HOW_HEARD_UUID]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0018_joinformquestion_and_custom_answers"),
    ]

    operations = [
        migrations.RunPython(seed_questions_and_migrate_answers, reverse_migrate),
    ]
