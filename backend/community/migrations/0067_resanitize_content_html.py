"""Retroactively sanitize `content_html` rows saved before the write-path guard shipped."""

from django.db import migrations

# Frozen snapshot for this one-shot backfill — not a living registry. New content
# models are sanitized on write by `render_content_payload`.
_CONTENT_MODELS = (
    "CommunityGuidelines",
    "FAQ",
    "HomePage",
    "EditablePage",
    "Document",
)


def resanitize(apps, schema_editor):
    from community._html_sanitize import sanitize_content_html

    for model_name in _CONTENT_MODELS:
        model = apps.get_model("community", model_name)
        for obj in model.objects.exclude(content_html=""):
            cleaned = sanitize_content_html(obj.content_html)
            if cleaned != obj.content_html:
                obj.content_html = cleaned
                obj.save(update_fields=["content_html"])


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0066_backfill_joinrequest_names"),
    ]

    operations = [
        migrations.RunPython(resanitize, migrations.RunPython.noop),
    ]
