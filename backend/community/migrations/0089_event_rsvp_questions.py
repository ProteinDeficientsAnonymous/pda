import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0088_join_form_question_types"),
    ]

    operations = [
        migrations.AddField(
            model_name="eventrsvp",
            name="answers",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.CreateModel(
            name="EventRsvpQuestion",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("label", models.CharField(max_length=300)),
                (
                    "field_type",
                    models.CharField(
                        choices=[
                            ("textarea", "Text area"),
                            ("dropdown", "Dropdown"),
                            ("multiselect", "Multi select"),
                        ],
                        max_length=20,
                    ),
                ),
                ("options", models.JSONField(blank=True, default=list)),
                ("required", models.BooleanField(default=False)),
                ("display_order", models.PositiveIntegerField(default=0)),
                (
                    "event",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="rsvp_questions",
                        to="community.event",
                    ),
                ),
            ],
            options={"ordering": ["display_order"]},
        ),
    ]
