"""Re-sanitize existing rendered HTML through the nh3 chokepoint.

`sanitize_content_html` is applied on the write path (`render_content_payload`),
so it only protects content saved AFTER it shipped. Rows rendered earlier (e.g.
backfilled by migration 0037, which ran `delta_to_html` with no scheme/tag
validation) still hold un-sanitized `content_html`, which non-browser consumers
(emails, API clients) read verbatim. Run every existing row back through the
sanitizer so the security boundary is retroactive.
"""

from django.db import migrations

# Models carrying a rendered `content_html` column, as of this migration. This
# is a frozen point-in-time snapshot — a one-shot backfill, NOT a living
# registry. Do not edit it when new content models are added later; their rows
# are sanitized on write by `render_content_payload`.
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
        ("community", "0057_joinrequest_email"),
    ]

    operations = [
        # Re-running the sanitizer is idempotent (already-clean rows are skipped),
        # so reversing this migration is a no-op rather than an error.
        migrations.RunPython(resanitize, migrations.RunPython.noop),
    ]
