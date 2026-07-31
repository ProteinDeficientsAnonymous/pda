from django.db import migrations


def add_creators_to_cohosts(apps, schema_editor):
    # Bulk insert via the through table instead of per-event .add() to avoid N+1 queries.
    Event = apps.get_model("community", "Event")
    through = Event.co_hosts.through
    existing = set(through.objects.values_list("event_id", "user_id"))
    rows = [
        through(event_id=event_id, user_id=created_by_id)
        for event_id, created_by_id in Event.objects.filter(
            created_by__isnull=False,
        ).values_list("id", "created_by_id")
        if (event_id, created_by_id) not in existing
    ]
    through.objects.bulk_create(rows, batch_size=1000)


def noop_reverse(apps, schema_editor):
    """Irreversible in practice: seeded creators are indistinguishable from
    hand-added co-hosts, so reverse can't safely strip them. Harmless to leave."""


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0084_event_checkin_nudge_sent_at"),
    ]

    operations = [
        migrations.RunPython(add_creators_to_cohosts, noop_reverse),
    ]
