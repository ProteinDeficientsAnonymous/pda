import asyncio
import logging

import pytest
from audit.models import AuditLogEntry, AuditTargetType
from community.join_requests import check_in_promotion
from community.models import Event, EventType
from community.validation import Code, InvalidStateTransition, TransitionFailure
from config.audit import AuditTarget, actor_request, audit_log, audit_rejected_transition
from config.validation_handlers import register_validation_handlers, serialize_validation_exception
from django.db import transaction
from django.test import RequestFactory
from django.utils import timezone
from hypothesis import given
from hypothesis import strategies as st
from mcp.server.mcpserver.exceptions import ToolError
from mcp_gateway.view_calls import call_view
from ninja import NinjaAPI
from ninja.testing import TestClient
from users.models import MembershipStatus, User

from tests._users import make_user

_SAFE_TEXT = st.text(alphabet=st.characters(blacklist_categories=("Cs",)), min_size=1, max_size=32)
_FAILURE_ST = st.builds(
    TransitionFailure,
    action=_SAFE_TEXT,
    target_type=st.sampled_from([AuditTargetType.USER, AuditTargetType.JOIN_REQUEST]),
    target_id=_SAFE_TEXT,
    event=_SAFE_TEXT,
    from_status=_SAFE_TEXT,
    to_status=st.one_of(st.none(), _SAFE_TEXT),
    extra=st.one_of(
        st.none(),
        st.dictionaries(
            keys=st.sampled_from(["note", "full_name", "reason"]),
            values=_SAFE_TEXT,
            min_size=1,
            max_size=3,
        ),
    ),
)


class TestTransitionFailureUnit:
    @pytest.mark.unit
    def test_transition_failure_details_merges_core_and_extra_fields(self):
        failure = TransitionFailure(
            action="user_transition_rejected",
            target_type=AuditTargetType.USER,
            target_id="u-1",
            event="pause_for_attendance",
            from_status="guidelines_paused",
            to_status="attendance_paused",
            extra={"reason": "blocked"},
        )

        details = failure.details(Code.User.GUIDELINES_PAUSED)

        assert details == {
            "event": "pause_for_attendance",
            "from": "guidelines_paused",
            "to": "attendance_paused",
            "code": Code.User.GUIDELINES_PAUSED,
            "reason": "blocked",
        }

    @pytest.mark.unit
    def test_invalid_state_transition_serializes_without_leaking_audit_fields(self):
        failure = TransitionFailure(
            action="user_transition_rejected",
            target_type=AuditTargetType.USER,
            target_id="secret-id",
            event="lift_attendance_pause",
            from_status="attendance_paused",
            to_status="active_member",
        )
        exc = InvalidStateTransition(
            Code.User.ATTENDANCE_PAUSE_LIFTS_ON_CHECK_IN,
            failure,
            field="attendance_paused",
        )

        payload = serialize_validation_exception(exc)

        assert payload == {
            "code": Code.User.ATTENDANCE_PAUSE_LIFTS_ON_CHECK_IN,
            "field": "attendance_paused",
        }

    @pytest.mark.unit
    @given(failure=_FAILURE_ST, field=st.one_of(st.none(), _SAFE_TEXT))
    def test_invalid_state_transition_property_preserves_wire_and_audit_shapes(
        self, failure, field
    ):
        exc = InvalidStateTransition(
            Code.JoinRequest.ALREADY_DECIDED,
            failure,
            field=field,
        )

        wire = serialize_validation_exception(exc)
        details = exc.failure.details(exc.code)

        assert set(wire.keys()) <= {"code", "field", "params"}
        assert wire["code"] == Code.JoinRequest.ALREADY_DECIDED
        assert wire["field"] == field
        assert details["event"] == failure.event
        assert details["from"] == failure.from_status
        assert details["to"] == failure.to_status
        assert details["code"] == Code.JoinRequest.ALREADY_DECIDED
        for k, v in (failure.extra or {}).items():
            assert details[k] == v


def _make_failing_route_api(namespace: str, actor: User) -> NinjaAPI:
    test_api = NinjaAPI(urls_namespace=namespace, auth=lambda request: actor)
    register_validation_handlers(test_api)

    @test_api.post("/fail/{user_id}/")
    def fail_inside_atomic(request, user_id: str):
        with transaction.atomic():
            target = User.objects.select_for_update().get(pk=user_id)
            target.first_name = "MutatedBeforeRollback"
            target.save(update_fields=["first_name"])
            raise InvalidStateTransition(
                Code.User.GUIDELINES_PAUSED,
                TransitionFailure(
                    action="user_transition_rejected",
                    target_type=AuditTargetType.USER,
                    target_id=str(target.pk),
                    event="pause_for_attendance",
                    from_status="guidelines_paused",
                    to_status="attendance_paused",
                ),
                field="attendance_paused",
            )

    return test_api


@pytest.mark.integration
class TestTransitionAuditPersistence:
    @pytest.mark.django_db(transaction=True)
    def test_ninja_handler_persists_rejected_transition_after_atomic_rollback(self):
        actor = make_user(first_name="Admin", last_name="Actor")
        subject = make_user(first_name="Original")
        client = TestClient(_make_failing_route_api("transition_audit_ninja", actor))

        response = client.post(
            f"/fail/{subject.pk}/",
            META={"REMOTE_ADDR": "198.51.100.42"},
        )

        assert response.status_code == 400
        subject.refresh_from_db()
        assert subject.first_name == "Original"
        entry = AuditLogEntry.objects.get(
            action="user_transition_rejected", target_id=str(subject.pk)
        )
        assert entry.actor_id == actor.pk
        assert entry.ip_address == "198.51.100.42"
        assert entry.level == logging.WARNING
        assert entry.target_type == AuditTargetType.USER
        assert entry.details == {
            "event": "pause_for_attendance",
            "from": "guidelines_paused",
            "to": "attendance_paused",
            "code": Code.User.GUIDELINES_PAUSED,
        }

    @pytest.mark.django_db(transaction=True)
    def test_mcp_call_view_persists_rejected_transition_with_mcp_marker(self):
        actor = make_user(first_name="Mcp", last_name="Caller")
        subject = make_user(first_name="Unchanged")

        def failing_view(request, user_id: str):
            with transaction.atomic():
                target = User.objects.select_for_update().get(pk=user_id)
                target.first_name = "ShouldRollback"
                target.save(update_fields=["first_name"])
                raise InvalidStateTransition(
                    Code.User.ATTENDANCE_PAUSE_LIFTS_ON_CHECK_IN,
                    TransitionFailure(
                        action="user_transition_rejected",
                        target_type=AuditTargetType.USER,
                        target_id=str(target.pk),
                        event="lift_attendance_pause",
                        from_status="attendance_paused",
                        to_status="active_member",
                    ),
                    field="attendance_paused",
                )

        with pytest.raises(ToolError):
            asyncio.run(call_view(failing_view, actor, user_id=str(subject.pk)))

        subject.refresh_from_db()
        assert subject.first_name == "Unchanged"
        entry = AuditLogEntry.objects.get(
            action="user_transition_rejected", target_id=str(subject.pk)
        )
        assert entry.actor_id == actor.pk
        assert entry.details["via"] == "mcp"
        assert entry.details["event"] == "lift_attendance_pause"
        assert entry.details["code"] == Code.User.ATTENDANCE_PAUSE_LIFTS_ON_CHECK_IN

    @pytest.mark.django_db
    def test_check_in_promotion_failure_records_transition_details(
        self, monkeypatch, django_capture_on_commit_callbacks
    ):
        host = make_user(first_name="Host")
        guest = make_user(first_name="Guest", membership_status=MembershipStatus.TENTATIVE)
        event = Event.objects.create(
            title="Meetup",
            start_datetime=timezone.now(),
            event_type=EventType.OFFICIAL,
            created_by=host,
        )

        def fail_promote(user, ev, actor):
            raise InvalidStateTransition(
                Code.JoinRequest.ALREADY_DECIDED,
                TransitionFailure(
                    action="join_request_transition_rejected",
                    target_type=AuditTargetType.JOIN_REQUEST,
                    target_id="jr-stale",
                    event="approve",
                    from_status="closed",
                    to_status="approved",
                ),
            )

        monkeypatch.setattr(check_in_promotion, "maybe_promote_tentative", fail_promote)
        monkeypatch.setattr(
            check_in_promotion, "notify_vetters_promotion_failed", lambda u, e: None
        )
        request = RequestFactory().post("/")
        request.auth = host

        with django_capture_on_commit_callbacks(execute=True):
            outcome = check_in_promotion.promote_or_restore_on_check_in(request, guest, event)

        assert outcome is None
        entry = AuditLogEntry.objects.get(
            action="check_in_promotion_failed", target_id=str(guest.pk)
        )
        assert entry.details == {
            "event_id": str(event.pk),
            "error": "InvalidStateTransition",
            "event": "approve",
            "from": "closed",
            "to": "approved",
            "code": Code.JoinRequest.ALREADY_DECIDED,
        }

    @pytest.mark.django_db
    def test_audit_rejected_transition_repeated_call_persists_once(
        self, django_capture_on_commit_callbacks
    ):
        actor = make_user(first_name="Once")
        exc = InvalidStateTransition(
            Code.JoinRequest.ALREADY_DECIDED,
            TransitionFailure(
                action="join_request_transition_rejected",
                target_type=AuditTargetType.JOIN_REQUEST,
                target_id="jr-123",
                event="approve",
                from_status="closed",
                to_status="approved",
            ),
        )

        with django_capture_on_commit_callbacks(execute=True):
            audit_rejected_transition(None, exc, actor=actor)
            audit_rejected_transition(None, exc, actor=actor)

        entries = AuditLogEntry.objects.filter(target_id="jr-123")
        assert entries.count() == 1
        entry = entries.get()
        assert entry.actor_id == actor.pk
        assert entry.ip_address is None

    @pytest.mark.django_db
    def test_audit_log_without_request_uses_actor_carrier(self, django_capture_on_commit_callbacks):
        actor = make_user(first_name="System", last_name="Runner")

        with django_capture_on_commit_callbacks(execute=True):
            audit_log(
                logging.INFO,
                "user_promoted_on_check_in",
                actor_request(None, actor),
                target=AuditTarget(type=AuditTargetType.USER, id=str(actor.pk)),
            )

        entry = AuditLogEntry.objects.get(action="user_promoted_on_check_in")
        assert entry.actor_id == actor.pk
        assert entry.ip_address is None
