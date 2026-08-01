from django.db import migrations, models

from community.models.event import build_event_slug


def backfill_slugs(apps, schema_editor):
    Event = apps.get_model("community", "Event")
    for event in Event.objects.filter(slug="").order_by("created_at").iterator():
        event.slug = build_event_slug(event.title, Event.objects, exclude_pk=event.pk)
        event.save(update_fields=["slug"])


def noop_reverse(apps, schema_editor):
    """Nothing to undo — the column itself is dropped by the reverse AddField."""


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0085_backfill_creator_as_cohost"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="slug",
            field=models.SlugField(blank=True, db_index=False, default="", max_length=80),
            preserve_default=False,
        ),
        migrations.RunPython(backfill_slugs, noop_reverse),
        migrations.AlterField(
            model_name="event",
            name="slug",
            field=models.SlugField(blank=True, max_length=80, unique=True),
        ),
    ]
