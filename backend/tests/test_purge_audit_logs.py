import logging
from datetime import timedelta
from io import StringIO

import pytest
from audit.models import AuditLogEntry
from django.core.management import call_command
from django.utils import timezone


def make_entry(age_days: int) -> AuditLogEntry:
    entry = AuditLogEntry.objects.create(
        action="role_created", actor_label="someone", level=logging.INFO
    )
    # created_at is auto_now_add, so backdating needs a direct update.
    AuditLogEntry.objects.filter(pk=entry.pk).update(
        created_at=timezone.now() - timedelta(days=age_days)
    )
    return entry


def run(*args) -> str:
    out = StringIO()
    call_command("purge_audit_logs", *args, stdout=out)
    return out.getvalue()


@pytest.mark.django_db
class TestPurgeAuditLogs:
    def test_deletes_only_entries_past_retention(self):
        old = make_entry(400)
        recent = make_entry(10)

        run()

        assert list(AuditLogEntry.objects.values_list("pk", flat=True)) == [recent.pk]
        assert not AuditLogEntry.objects.filter(pk=old.pk).exists()

    def test_respects_custom_days(self):
        make_entry(40)
        kept = make_entry(10)

        run("--days", "30")

        assert list(AuditLogEntry.objects.values_list("pk", flat=True)) == [kept.pk]

    def test_dry_run_deletes_nothing(self):
        make_entry(400)

        output = run("--dry-run")

        assert "would delete 1 entries" in output
        assert AuditLogEntry.objects.count() == 1

    def test_entry_exactly_at_boundary_is_kept(self):
        make_entry(365)

        run("--days", "366")

        assert AuditLogEntry.objects.count() == 1

    def test_rejects_zero_days(self):
        make_entry(400)
        err = StringIO()

        call_command("purge_audit_logs", "--days", "0", stderr=err)

        assert "at least 1" in err.getvalue()
        assert AuditLogEntry.objects.count() == 1
