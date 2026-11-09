import logging
import re
from pathlib import Path

import pytest
from audit.models import AuditLogEntry, AuditTargetType
from config.audit import (
    AuditTarget,
    audit_log,
    audit_log_before_raise,
    flush_rollback_safe_audits,
)
from django.db import transaction
from django.test import RequestFactory
from users.models import MagicLoginToken


@pytest.fixture
def request_with_actor(test_user):
    request = RequestFactory().get("/")
    request.META["REMOTE_ADDR"] = "203.0.113.7"
    request.auth = test_user
    return request


@pytest.fixture
def anon_request():
    request = RequestFactory().get("/")
    request.META["REMOTE_ADDR"] = "203.0.113.9"
    return request


@pytest.fixture
def commit(django_capture_on_commit_callbacks):

    def run(fn):
        with django_capture_on_commit_callbacks(execute=True):
            fn()

    return run


class TestAuditPersistence:
    def test_persists_row(self, db, commit, request_with_actor, test_user):
        commit(
            lambda: audit_log(
                logging.INFO,
                "role_created",
                request_with_actor,
                target=AuditTarget(type=AuditTargetType.ROLE, id="abc", details={"name": "vettor"}),
            )
        )

        entry = AuditLogEntry.objects.get()
        assert entry.action == "role_created"
        assert entry.actor_id == test_user.pk
        assert entry.target_type == AuditTargetType.ROLE
        assert entry.target_id == "abc"
        assert entry.details == {"name": "vettor"}
        assert entry.ip_address == "203.0.113.7"
        assert entry.level == logging.INFO

    def test_persist_false_writes_no_row(self, db, commit, request_with_actor):
        commit(
            lambda: audit_log(
                logging.WARNING,
                "permission_denied",
                request_with_actor,
                persist=False,
                target=AuditTarget(type=AuditTargetType.ROLE),
            )
        )

        assert not AuditLogEntry.objects.exists()

    def test_anonymous_actor_persists_with_null_fk(self, db, commit, anon_request):
        commit(lambda: audit_log(logging.INFO, "join_request_submitted", anon_request))

        entry = AuditLogEntry.objects.get()
        assert entry.actor is None
        assert entry.actor_label == "anonymous"

    def test_actor_label_survives_actor_deletion(self, db, commit, request_with_actor, test_user):
        commit(lambda: audit_log(logging.WARNING, "user_archived", request_with_actor))
        label = AuditLogEntry.objects.get().actor_label

        test_user.delete()

        entry = AuditLogEntry.objects.get()
        assert entry.actor is None
        assert entry.actor_label == label

    def test_write_failure_does_not_propagate(
        self, db, commit, request_with_actor, monkeypatch, caplog
    ):
        def boom(**kwargs):
            raise RuntimeError("db is on fire")

        monkeypatch.setattr(AuditLogEntry.objects, "create", boom)

        audit_logger = logging.getLogger("pda.audit")
        audit_logger.addHandler(caplog.handler)
        try:
            with caplog.at_level(logging.ERROR, logger="pda.audit"):
                commit(lambda: audit_log(logging.INFO, "role_created", request_with_actor))
        finally:
            audit_logger.removeHandler(caplog.handler)

        assert "audit_persist_failed" in caplog.text

    def test_no_row_when_transaction_rolls_back(self, db, request_with_actor):
        class Rollback(Exception):
            pass

        with pytest.raises(Rollback), transaction.atomic():
            audit_log(logging.INFO, "role_created", request_with_actor)
            raise Rollback

        assert not AuditLogEntry.objects.exists()

    @pytest.mark.parametrize("bad_ip", ["anon", "not-an-ip", ""])
    def test_unparseable_ip_stored_as_null(self, db, commit, test_user, bad_ip):
        request = RequestFactory().get("/")
        request.META["REMOTE_ADDR"] = bad_ip
        request.auth = test_user

        commit(lambda: audit_log(logging.INFO, "role_created", request))

        assert AuditLogEntry.objects.get().ip_address is None


class TestSurviveRollback:
    class Rollback(Exception):
        pass

    def test_held_row_written_after_rollback(self, db, request_with_actor):
        with pytest.raises(self.Rollback), transaction.atomic():
            audit_log_before_raise(logging.WARNING, "login_archived", request_with_actor)
            raise self.Rollback

        assert not AuditLogEntry.objects.exists()
        flush_rollback_safe_audits(request_with_actor)
        flush_rollback_safe_audits(request_with_actor)

        assert AuditLogEntry.objects.get().action == "login_archived"

    @pytest.mark.parametrize(
        ("field", "action"),
        [("archived_at", "magic_login_archived"), ("is_paused", "magic_login_paused")],
    )
    def test_blocked_magic_login_audit_persists(self, api_client, test_user, field, action):
        setattr(test_user, field, True if field == "is_paused" else test_user.date_joined)
        test_user.save(update_fields=[field])
        magic = MagicLoginToken.create_for_user(test_user)

        response = api_client.get(f"/api/auth/magic-login/{magic.token}/")

        assert response.status_code == 403
        entry = AuditLogEntry.objects.get(action=action)
        assert entry.target_id == str(test_user.pk)


class TestAuditTargetTypeCoverage:
    def test_every_call_site_uses_a_valid_enum_member(self):
        backend = Path(__file__).resolve().parent.parent
        literals = []
        for path in backend.rglob("*.py"):
            if "tests" in path.parts or "migrations" in path.parts:
                continue
            for match in re.finditer(
                r'AuditTarget\([^)]*type=(["\'])([^"\']*)\1', path.read_text()
            ):
                literals.append((path.name, match.group(2)))

        assert literals == [], f"raw target_type literals found: {literals}"
