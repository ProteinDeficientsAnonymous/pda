from django.db import migrations

SET_ACTION = "guest_payment_changed"
REVOKE_ACTION = "guest_payment_revoked"
EVENT_TARGET = "event"


def _latest_host_payment_entries(AuditLogEntry) -> dict:
    # Oldest first so the last host toggle per (event, guest) wins.
    latest = {}
    entries = AuditLogEntry.objects.filter(
        action__in=(SET_ACTION, REVOKE_ACTION), target_type=EVENT_TARGET
    ).order_by("created_at")
    for entry in entries:
        user_id = (entry.details or {}).get("user_id")
        if user_id:
            latest[(entry.target_id, str(user_id))] = entry
    return latest


def _is_set_paid(entry) -> bool:
    # A redundant clear on an unpaid guest also logs as guest_payment_changed, with paid false.
    return entry.action == SET_ACTION and (entry.details or {}).get("paid_confirmed") is True


def _host_stamped(entry, rsvp) -> bool:
    # The old toggle stamped paid_confirmed_at a few ms before writing the audit row.
    details = entry.details or {}
    return (
        details.get("was_paid") is False
        and details.get("paid_confirmed_at") == rsvp.paid_confirmed_at.isoformat()
    )


def backfill_payment_verified(apps, schema_editor):
    AuditLogEntry = apps.get_model("audit", "AuditLogEntry")
    EventRSVP = apps.get_model("community", "EventRSVP")

    set_paid = {
        key: entry
        for key, entry in _latest_host_payment_entries(AuditLogEntry).items()
        if _is_set_paid(entry)
    }
    if not set_paid:
        return

    event_ids = {event_id for event_id, _ in set_paid}
    updated = []
    candidates = EventRSVP.objects.filter(
        event_id__in=event_ids,
        paid_confirmed_at__isnull=False,
        payment_verified_at__isnull=True,
    ).only("id", "event_id", "user_id", "created_at", "paid_confirmed_at")
    for rsvp in candidates.iterator():
        entry = set_paid.get((str(rsvp.event_id), str(rsvp.user_id)))
        # A removed-and-recreated rsvp must not inherit the old row's verification.
        if entry is None or entry.created_at < rsvp.created_at:
            continue
        rsvp.payment_verified_at = (
            rsvp.paid_confirmed_at if _host_stamped(entry, rsvp) else entry.created_at
        )
        rsvp.payment_verified_by_id = entry.actor_id
        updated.append(rsvp)
    EventRSVP.objects.bulk_update(
        updated, ["payment_verified_at", "payment_verified_by"], batch_size=500
    )


class Migration(migrations.Migration):
    dependencies = [
        ("audit", "0004_mcp_connection_target_type"),
        ("community", "0113_eventrsvp_payment_verified"),
    ]

    operations = [
        migrations.RunPython(backfill_payment_verified, migrations.RunPython.noop),
    ]
