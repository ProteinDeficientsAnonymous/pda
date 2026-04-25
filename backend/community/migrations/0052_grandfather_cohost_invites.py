"""Backfill EventCoHostInvite rows as ACCEPTED for every existing event.co_hosts entry.

Existing co-hosts are grandfathered silently — no notifications fire.
"""

from django.db import migrations


def grandfather_cohosts(apps, schema_editor):
    Event = apps.get_model("community", "Event")
    EventCoHostInvite = apps.get_model("community", "EventCoHostInvite")

    invites = []
    for event in Event.objects.all().prefetch_related("co_hosts"):
        for user in event.co_hosts.all():
            invites.append(
                EventCoHostInvite(
                    event=event,
                    user=user,
                    invited_by_id=event.created_by_id,
                    status="accepted",
                    decided_at=event.created_at,
                )
            )
    if invites:
        EventCoHostInvite.objects.bulk_create(invites, ignore_conflicts=True)


def unbackfill(apps, schema_editor):
    # Reverse is a noop: deleting all "accepted" invites would also wipe any real
    # acceptances created after this migration ran. The schema migration that
    # created the table is reversible on its own (drops the table entirely).
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0051_event_cohost_invite"),
    ]

    operations = [
        migrations.RunPython(grandfather_cohosts, unbackfill),
    ]
