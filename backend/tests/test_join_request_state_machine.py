import uuid
from dataclasses import dataclass

import pytest
from audit.models import AuditLogEntry, AuditTargetType
from community.models import (
    ALLOWED_JOIN_REQUEST_TRANSITIONS,
    AttendanceStatus,
    Event,
    EventRSVP,
    EventType,
    JoinRequest,
    JoinRequestEvent,
    JoinRequestStatus,
    RejectionReason,
    RSVPStatus,
)
from community.validation import Code, InvalidStateTransition, ValidationException
from django.utils import timezone
from hypothesis import settings
from hypothesis.stateful import RuleBasedStateMachine, invariant, rule
from hypothesis.strategies import sampled_from
from users.models import MembershipEvent, MembershipStatus, User
from users.permissions import PermissionKey
from users.roles import Role

from tests._asserts import assert_error_code
from tests._auth import auth_headers_for
from tests._events import make_event
from tests._public_rsvp_helpers import make_official_event
from tests._public_rsvp_helpers import post as post_public_rsvp
from tests._users import make_user


def _in_memory_actor() -> User:
    return User(
        id=uuid.uuid4(),
        phone_number="+13125558888",
        first_name="Vettor",
        membership_status=MembershipStatus.ACTIVE_MEMBER,
    )


def _in_memory_event(creator: User) -> Event:
    return Event(
        id=uuid.uuid4(),
        title="Official Gathering",
        event_type=EventType.OFFICIAL,
        created_by=creator,
        start_datetime=timezone.now(),
    )


def _in_memory_jr(status: JoinRequestStatus = JoinRequestStatus.PENDING) -> JoinRequest:
    return JoinRequest(
        id=uuid.uuid4(),
        first_name="Sprout",
        last_name="Vegan",
        phone_number="+14155550177",
        email="sprout@example.com",
        status=status,
        rejection_reason=RejectionReason.VEGETARIAN if status == JoinRequestStatus.REJECTED else "",
        rejection_note="note" if status == JoinRequestStatus.REJECTED else "",
    )


def _jr_snapshot(jr: JoinRequest) -> tuple:
    return (
        jr.status,
        jr.status_changed_at,
        jr.status_changed_by_id,
        jr.approved_via_event_id,
        jr.rejection_reason,
        jr.rejection_note,
    )


def _fire_jr_event(jr: JoinRequest, event: JoinRequestEvent, actor: User, ev: Event) -> list[str]:
    if event == JoinRequestEvent.MARK_TENTATIVE:
        return jr.mark_tentative(by=actor)
    if event == JoinRequestEvent.APPROVE:
        return jr.approve(by=actor)
    if event == JoinRequestEvent.PROMOTE_ON_CHECK_IN:
        return jr.promote_on_check_in(event=ev, by=actor)
    if event == JoinRequestEvent.REJECT:
        return jr.reject(by=actor, reason=RejectionReason.VEGETARIAN, note="ignored")
    if event == JoinRequestEvent.UNREJECT:
        return jr.unreject(by=actor)
    return jr.close(by=actor)


def _expected_jr_rejection_code(status: JoinRequestStatus, event: JoinRequestEvent) -> str:
    if event == JoinRequestEvent.UNREJECT:
        return Code.JoinRequest.ONLY_REJECTED_CAN_BE_UN_REJECTED
    if status == JoinRequestStatus.TENTATIVE and event == JoinRequestEvent.REJECT:
        return Code.JoinRequest.TENTATIVE_CANNOT_BE_REJECTED
    if status == JoinRequestStatus.PENDING and event in (
        JoinRequestEvent.CLOSE,
        JoinRequestEvent.PROMOTE_ON_CHECK_IN,
    ):
        return Code.JoinRequest.INVALID_STATUS
    return Code.JoinRequest.ALREADY_DECIDED


class TestJoinRequestStateMachineUnit:
    @pytest.mark.unit
    @pytest.mark.parametrize("status", list(JoinRequestStatus))
    @pytest.mark.parametrize("event", list(JoinRequestEvent))
    def test_matrix_enforces_exact_allowed_edges_and_stamps(
        self, status: JoinRequestStatus, event: JoinRequestEvent
    ):
        actor = _in_memory_actor()
        ev = _in_memory_event(actor)
        jr = _in_memory_jr(status)
        before = _jr_snapshot(jr)
        expected = ALLOWED_JOIN_REQUEST_TRANSITIONS.get((status, event))

        if expected is None:
            with pytest.raises(InvalidStateTransition) as exc_info:
                _fire_jr_event(jr, event, actor, ev)
            assert _jr_snapshot(jr) == before
            exc = exc_info.value
            assert (exc.failure.action, exc.failure.target_type, exc.failure.target_id) == (
                "join_request_transition_rejected",
                AuditTargetType.JOIN_REQUEST,
                str(jr.id),
            )
            assert (exc.failure.event, exc.failure.from_status) == (event, status)
            assert exc.code == _expected_jr_rejection_code(status, event)
            return

        fields = _fire_jr_event(jr, event, actor, ev)
        assert "status" in fields
        assert jr.status == expected
        assert jr.status_changed_at is not None
        assert jr.status_changed_by == actor
        assert (jr.approved_via_event == ev) == (event == JoinRequestEvent.PROMOTE_ON_CHECK_IN)
        if event == JoinRequestEvent.UNREJECT:
            assert (jr.rejection_reason, jr.rejection_note) == ("", "")
        if event == JoinRequestEvent.REJECT:
            assert (jr.rejection_reason, jr.rejection_note) == (RejectionReason.VEGETARIAN, "")

    @pytest.mark.unit
    def test_promote_on_check_in_requires_event(self):
        actor = _in_memory_actor()
        jr = _in_memory_jr(JoinRequestStatus.TENTATIVE)
        before = _jr_snapshot(jr)

        with pytest.raises(InvalidStateTransition):
            jr.promote_on_check_in(event=None, by=actor)

        assert _jr_snapshot(jr) == before

    @pytest.mark.unit
    def test_reject_validates_reason_without_mutating_pending_status(self):
        actor = _in_memory_actor()
        jr = _in_memory_jr(JoinRequestStatus.PENDING)
        before = _jr_snapshot(jr)

        with pytest.raises(ValidationException) as exc_info:
            jr.reject(by=actor, reason=RejectionReason.OTHER, note="   ")

        assert exc_info.value.code == Code.JoinRequest.REJECTION_NOTE_REQUIRED
        assert exc_info.value.status_code == 422
        assert _jr_snapshot(jr) == before


@dataclass
class _CoupledStep:
    promoted_via_event: bool = False


def _sync_user_on_jr_event(
    user: User, event: JoinRequestEvent, actor: User, meta: _CoupledStep
) -> None:
    if event == JoinRequestEvent.MARK_TENTATIVE and (
        user.is_archived or user.membership_status == MembershipStatus.NONE
    ):
        user.mark_tentative(by=actor)
    elif event == JoinRequestEvent.APPROVE and (
        user.is_archived
        or user.membership_status in (MembershipStatus.NONE, MembershipStatus.TENTATIVE)
    ):
        user.approve_membership(by=actor)
    elif event == JoinRequestEvent.PROMOTE_ON_CHECK_IN:
        meta.promoted_via_event = True
        if not user.is_archived and user.membership_status == MembershipStatus.TENTATIVE:
            user.promote_on_check_in(by=actor)


@settings(max_examples=75, stateful_step_count=30)
class CoupledJoinAndUserMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.actor = _in_memory_actor()
        self.ev = _in_memory_event(self.actor)
        self.user = User(
            id=uuid.uuid4(),
            phone_number="+14155550177",
            first_name="Sprout",
            membership_status=MembershipStatus.NONE,
        )
        self.requests: list[tuple[JoinRequest, _CoupledStep]] = [
            (_in_memory_jr(JoinRequestStatus.PENDING), _CoupledStep())
        ]

    @rule(event=sampled_from(list(JoinRequestEvent)))
    def step_join_request(self, event: JoinRequestEvent):
        jr, meta = self.requests[-1]
        jr_before = _jr_snapshot(jr)
        if (
            event == JoinRequestEvent.CLOSE
            and not self.user.is_archived
            and self.user.membership_status == MembershipStatus.TENTATIVE
        ):
            self.user.archive(by=self.actor)
        try:
            _fire_jr_event(jr, event, self.actor, self.ev)
        except InvalidStateTransition:
            assert _jr_snapshot(jr) == jr_before
            return
        _sync_user_on_jr_event(self.user, event, self.actor, meta)

    @rule(
        event=sampled_from(
            [
                MembershipEvent.PAUSE_FOR_ATTENDANCE,
                MembershipEvent.RESTORE_ON_CHECK_IN,
                MembershipEvent.PAUSE_FOR_GUIDELINES,
                MembershipEvent.LIFT_GUIDELINES_PAUSE,
                MembershipEvent.ARCHIVE,
            ]
        )
    )
    def step_user(self, event: MembershipEvent):
        jr, _ = self.requests[-1]
        if event == MembershipEvent.ARCHIVE:
            try:
                self.user.archive(by=self.actor)
            except InvalidStateTransition:
                return
            if jr.status == JoinRequestStatus.TENTATIVE:
                jr.close(by=self.actor)
            return
        caller = {
            MembershipEvent.PAUSE_FOR_ATTENDANCE: self.user.apply_attendance_pause,
            MembershipEvent.RESTORE_ON_CHECK_IN: self.user.restore_on_check_in,
            MembershipEvent.PAUSE_FOR_GUIDELINES: self.user.apply_guidelines_pause,
            MembershipEvent.LIFT_GUIDELINES_PAUSE: self.user.lift_guidelines_pause,
        }[event]
        try:
            caller(by=self.actor)
        except InvalidStateTransition:
            return

    @rule()
    def reapply_when_no_open_request(self):
        open_exists = any(
            jr.status in (JoinRequestStatus.PENDING, JoinRequestStatus.TENTATIVE)
            for jr, _ in self.requests
        )
        can_reapply = self.user.is_archived or self.user.membership_status == MembershipStatus.NONE
        if not open_exists and can_reapply:
            self.requests.append((_in_memory_jr(JoinRequestStatus.PENDING), _CoupledStep()))

    @invariant()
    def coupled_invariants_hold(self):
        open_reqs = [
            jr
            for jr, _ in self.requests
            if jr.status in (JoinRequestStatus.PENDING, JoinRequestStatus.TENTATIVE)
        ]
        assert len(open_reqs) <= 1
        for jr, meta in self.requests:
            assert (jr.approved_via_event is not None) == meta.promoted_via_event
            if jr.status != JoinRequestStatus.REJECTED:
                assert (jr.rejection_reason, jr.rejection_note) == ("", "")
            if jr.status == JoinRequestStatus.TENTATIVE:
                assert not self.user.is_archived


TestCoupledJoinAndUserStateful = pytest.mark.unit(CoupledJoinAndUserMachine.TestCase)


def _submit_join_form(api_client, phone: str, email: str, why_join_id: str) -> str:
    resp = api_client.post(
        "/api/community/join-request/",
        {
            "first_name": "Phoenix",
            "last_name": "Applicant",
            "phone_number": phone,
            "email": email,
            "answers": {why_join_id: "liberation"},
            "sms_consent": True,
            "guidelines_consent": True,
        },
        content_type="application/json",
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _walk_first_request_to_closed(api_client, jr1_id: str, admin_headers: dict) -> User:
    bad_unreject = api_client.patch(
        f"/api/community/join-requests/{jr1_id}/unreject/",
        content_type="application/json",
        **admin_headers,
    )
    assert_error_code(bad_unreject, Code.JoinRequest.ONLY_REJECTED_CAN_BE_UN_REJECTED)

    assert (
        api_client.patch(
            f"/api/community/join-requests/{jr1_id}/",
            {"status": JoinRequestStatus.REJECTED, "rejection_reason": RejectionReason.VEGETARIAN},
            content_type="application/json",
            **admin_headers,
        ).status_code
        == 200
    )
    bad_approve = api_client.patch(
        f"/api/community/join-requests/{jr1_id}/",
        {"status": JoinRequestStatus.APPROVED},
        content_type="application/json",
        **admin_headers,
    )
    assert_error_code(bad_approve, Code.JoinRequest.ALREADY_DECIDED)

    assert (
        api_client.patch(
            f"/api/community/join-requests/{jr1_id}/unreject/",
            content_type="application/json",
            **admin_headers,
        ).status_code
        == 200
    )
    assert (
        api_client.patch(
            f"/api/community/join-requests/{jr1_id}/",
            {"status": JoinRequestStatus.TENTATIVE},
            content_type="application/json",
            **admin_headers,
        ).status_code
        == 200
    )
    user = User.objects.get(phone_number="+14155550123")
    user.needs_onboarding = False
    user.save(update_fields=["needs_onboarding"])

    # Sending TENTATIVE again is rejected and does NOT re-lock onboarding!
    repeat_tentative = api_client.patch(
        f"/api/community/join-requests/{jr1_id}/",
        {"status": JoinRequestStatus.TENTATIVE},
        content_type="application/json",
        **admin_headers,
    )
    assert_error_code(repeat_tentative, Code.JoinRequest.ALREADY_DECIDED)
    user.refresh_from_db()
    assert user.needs_onboarding is False

    bad_reject = api_client.patch(
        f"/api/community/join-requests/{jr1_id}/",
        {"status": JoinRequestStatus.REJECTED},
        content_type="application/json",
        **admin_headers,
    )
    assert_error_code(bad_reject, Code.JoinRequest.TENTATIVE_CANNOT_BE_REJECTED)

    assert api_client.delete(f"/api/auth/users/{user.pk}/", **admin_headers).status_code == 204
    bad_closed = api_client.patch(
        f"/api/community/join-requests/{jr1_id}/",
        {"status": JoinRequestStatus.APPROVED},
        content_type="application/json",
        **admin_headers,
    )
    assert_error_code(bad_closed, Code.JoinRequest.ALREADY_DECIDED)
    return user


@pytest.mark.integration
class TestJoinRequestLifecycleEndToEnd:
    @pytest.mark.django_db(transaction=True, serialized_rollback=True)
    def test_coupled_rsvp_vetting_archive_reapply_and_audit_trail(self, api_client, why_join_id):
        Role.objects.get_or_create(name="member", is_default=True)
        admin_user = make_user(
            PermissionKey.MANAGE_USERS,
            PermissionKey.APPROVE_JOIN_REQUESTS,
            PermissionKey.MANAGE_EVENTS,
            first_name="Coordinator",
        )
        admin_headers = auth_headers_for(admin_user)

        # Public RSVP creates NONE user (+14155550123, sam@example.com from helper)
        assert post_public_rsvp(api_client, make_official_event()).status_code in (200, 201)
        jr1_id = _submit_join_form(api_client, "+14155550123", "sam@example.com", why_join_id)
        user = _walk_first_request_to_closed(api_client, jr1_id, admin_headers)

        # Re-apply -> tentative -> check-in promotion
        jr2_id = _submit_join_form(api_client, "+14155550123", "sam@example.com", why_join_id)
        assert (
            api_client.patch(
                f"/api/community/join-requests/{jr2_id}/",
                {"status": JoinRequestStatus.TENTATIVE},
                content_type="application/json",
                **admin_headers,
            ).status_code
            == 200
        )
        ev = make_event(
            created_by=admin_user,
            event_type=EventType.OFFICIAL,
            start_datetime=timezone.now() - timezone.timedelta(hours=1),
        )
        EventRSVP.objects.create(event=ev, user=user, status=RSVPStatus.ATTENDING)
        assert (
            api_client.post(
                f"/api/community/events/{ev.id}/rsvps/{user.pk}/attendance/",
                {"attendance": AttendanceStatus.ATTENDED},
                content_type="application/json",
                **admin_headers,
            ).status_code
            == 200
        )

        user.refresh_from_db()
        jr2 = JoinRequest.objects.get(id=jr2_id)
        assert user.membership_status == MembershipStatus.ACTIVE_MEMBER
        assert jr2.status == JoinRequestStatus.APPROVED
        assert jr2.approved_via_event_id == ev.id

        jr1_logs = list(
            AuditLogEntry.objects.filter(
                target_type=AuditTargetType.JOIN_REQUEST, target_id=jr1_id
            ).order_by("created_at")
        )
        assert [e.action for e in jr1_logs] == [
            "join_request_submitted",
            "join_request_transition_rejected",
            "join_request_rejected",
            "join_request_transition_rejected",
            "join_request_unrejected",
            "join_request_tentative",
            "join_request_transition_rejected",
            "join_request_transition_rejected",
            "join_request_closed",
            "join_request_transition_rejected",
        ]
        jr2_logs = list(
            AuditLogEntry.objects.filter(
                target_type=AuditTargetType.JOIN_REQUEST, target_id=jr2_id
            ).order_by("created_at")
        )
        assert [e.action for e in jr2_logs] == [
            "join_request_submitted",
            "join_request_tentative",
            "join_request_approved",
        ]
        assert jr2_logs[-1].details["event"] == JoinRequestEvent.PROMOTE_ON_CHECK_IN
        assert jr2_logs[-1].details["approved_via_event_id"] == str(ev.id)
