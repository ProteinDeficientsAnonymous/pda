from django.db import migrations, models

# Remap values written by an earlier local 0086 that used RSVP-specific names.
_REMAP = {
    "free_response": "textarea",
    "select_one": "dropdown",
    "select_multiple": "multiselect",
}


def remap_field_types(apps, schema_editor):
    EventRsvpQuestion = apps.get_model("community", "EventRsvpQuestion")
    for old, new in _REMAP.items():
        EventRsvpQuestion.objects.filter(field_type=old).update(field_type=new)


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0086_eventrsvp_answers_eventrsvpquestion"),
    ]

    operations = [
        migrations.RunPython(remap_field_types, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="eventrsvpquestion",
            name="field_type",
            field=models.CharField(
                choices=[
                    ("textarea", "Text area"),
                    ("dropdown", "Dropdown"),
                    ("multiselect", "Multi select"),
                ],
                max_length=20,
            ),
        ),
    ]
