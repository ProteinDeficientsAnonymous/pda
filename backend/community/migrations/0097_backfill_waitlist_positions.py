from itertools import groupby

from django.db import migrations
from django.db.models import F


def backfill_positions(apps, schema_editor):
    EventRSVP = apps.get_model("community", "EventRSVP")
    rows = EventRSVP.objects.filter(status="waitlisted").order_by(
        "event_id", F("waitlist_position").asc(nulls_last=True), "created_at", "pk"
    )
    updated = []
    for _, group in groupby(rows, key=lambda r: r.event_id):
        for position, rsvp in enumerate(group, start=1):
            rsvp.waitlist_position = position
            updated.append(rsvp)
    EventRSVP.objects.bulk_update(updated, ["waitlist_position"], batch_size=500)


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0096_eventrsvp_waitlist_position"),
    ]

    operations = [
        migrations.RunPython(backfill_positions, migrations.RunPython.noop),
    ]
