import uuid
from dataclasses import dataclass

import pytest
from audit.models import AuditLogEntry, AuditTargetType
from community.models import AttendanceStatus, EventRSVP, EventType, JoinRequestStatus, RSVPStatus
from community.validation import Code, InvalidStateTransition
from django.utils import timezone
from hypothesis import settings
from hypothesis.stateful import RuleBasedStateMachine, initialize, invariant, rule
from hypothesis.strategies import sampled_from
from tests._asserts import assert_error_code
from tests._auth import auth_headers_for
from tests._events import make_event
from tests._mcp_tool_helpers import run_tool, tool_error
from tests._users import make_user
from users.models import (
    ALLOWED_MEMBERSHIP_TRANSITIONS,
    MANAGED_STATUSES,
    MEMBER_STATUSES,
    PAUSED_STATUSES,
    MembershipEvent,
    MembershipStatus,
    User,
)
from users.permissions import PermissionKey
from users.roles import Role


def _in_memory_user(
    status: MembershipStatus = MembershipStatus.ACTIVE_MEMBER,
    *,
    archived: bool = False,
    before_archive: MembershipStatus | None = None,
) -> User:
    now = timezone.now()
    return User(
        id=uuid.uuid4(),
        phone_number="+13125559999",
        first_name="State",
        last_name="Test",
        membership_status=MembershipStatus.ARCHIVED if archived else status,
        archived_at=now if archived else None,
        status_before_archive=before_archive,
        attendance_paused_at=(
            now
            if status == MembershipStatus.ATTENDANCE_PAUSED
            or before_archive == MembershipStatus.ATTENDANCE_PAUSED
            else None
        ),
        has_joined_whatsapp=True,
        calendar_token="cal-tok",
    )


def _snapshot(user: User) -> tuple:
    return (
        user.membership_status,
        user.membership_status_changed_at,
        user.membership_status_changed_by_id,
        user.archived_at,
        user.status_before_archive,
        user.attendance_paused_at,
        user.unpaused_at,
        user.restored_at,
        user.attendance_grace_notified_at,
        user.has_joined_whatsapp,
        user.calendar_token,
    )


_EVENT_CALLERS = {
    MembershipEvent.MARK_TENTATIVE: lambda u, by: u.mark_tentative(by=by),
    MembershipEvent.APPROVE: lambda u, by: u.approve_membership(by=by),
    MembershipEvent.PROMOTE_ON_CHECK_IN: lambda u, by: u.promote_on_check_in(by=by),
    MembershipEvent.PAUSE_FOR_ATTENDANCE: lambda u, by: u.apply_attendance_pause(by=by),
    MembershipEvent.LIFT_ATTENDANCE_PAUSE: lambda u, by: u.lift_attendance_pause(by=by),
    MembershipEvent.RESTORE_ON_CHECK_IN: lambda u, by: u.restore_on_check_in(by=by),
    MembershipEvent.PAUSE_FOR_GUIDELINES: lambda u, by: u.apply_guidelines_pause(by=by),
    MembershipEvent.LIFT_GUIDELINES_PAUSE: lambda u, by: u.lift_guidelines_pause(by=by),
    MembershipEvent.ARCHIVE: lambda u, by: u.archive(by=by),
}

_NON_ARCHIVED_STATUSES = [s for s in MembershipStatus if s != MembershipStatus.ARCHIVED]


_SPECIAL_REJECTION_CODES: dict[tuple[MembershipStatus, MembershipEvent], str] = {
    (MembershipStatus.GUIDELINES_PAUSED, MembershipEvent.PAUSE_FOR_ATTENDANCE): (
        Code.User.GUIDELINES_PAUSED
    ),
    (MembershipStatus.ATTENDANCE_PAUSED, MembershipEvent.LIFT_ATTENDANCE_PAUSE): (
        Code.User.ATTENDANCE_PAUSE_LIFTS_ON_CHECK_IN
    ),
}


def _assert_side_fields(user: User, status: MembershipStatus, event: MembershipEvent) -> None:
    if event == MembershipEvent.ARCHIVE:
        assert (user.archived_at is not None, user.status_before_archive, user.calendar_token) == (
            True,
            status,
            "",
        )
    elif event == MembershipEvent.LIFT_GUIDELINES_PAUSE:
        assert user.attendance_paused_at is not None and user.unpaused_at is not None
        assert user.has_joined_whatsapp is False
    elif event == MembershipEvent.PAUSE_FOR_ATTENDANCE:
        assert user.attendance_paused_at is not None and user.unpaused_at is None
        assert user.has_joined_whatsapp is False
    elif event == MembershipEvent.PAUSE_FOR_GUIDELINES:
        assert (user.attendance_paused_at, user.unpaused_at, user.has_joined_whatsapp) == (
            None,
            None,
            False,
        )
    elif event == MembershipEvent.RESTORE_ON_CHECK_IN:
        assert user.attendance_paused_at is None and user.restored_at is not None


class TestMembershipStateMachineUnit:
    @pytest.mark.unit
    def test_corrupt_membership_status_rejects_as_invalid_transition(self):
        actor = _in_memory_user(MembershipStatus.ACTIVE_MEMBER)
        user = _in_memory_user(MembershipStatus.ACTIVE_MEMBER)
        user.membership_status = "not_a_real_status"
        with pytest.raises(InvalidStateTransition) as exc_info:
            user.archive(by=actor)
        assert exc_info.value.code == Code.User.INVALID_STATUS_TRANSITION

    @pytest.mark.unit
    @pytest.mark.parametrize("status", _NON_ARCHIVED_STATUSES)
    @pytest.mark.parametrize("event", list(MembershipEvent))
    def test_non_archived_matrix_enforces_exact_allowed_edges(
        self, status: MembershipStatus, event: MembershipEvent
    ):
        actor = _in_memory_user(MembershipStatus.ACTIVE_MEMBER)
        user = _in_memory_user(status)
        before = _snapshot(user)
        expected = ALLOWED_MEMBERSHIP_TRANSITIONS.get((status, event))

        if expected is None:
            with pytest.raises(InvalidStateTransition) as exc_info:
                _EVENT_CALLERS[event](user, actor)
            assert _snapshot(user) == before
            exc = exc_info.value
            assert (exc.failure.action, exc.failure.target_type, exc.failure.target_id) == (
                "user_transition_rejected",
                AuditTargetType.USER,
                str(user.pk),
            )
            assert (exc.failure.event, exc.failure.from_status) == (event, status)
            assert exc.code == _SPECIAL_REJECTION_CODES.get(
                (status, event), Code.User.INVALID_STATUS_TRANSITION
            )
            return

        fields = _EVENT_CALLERS[event](user, actor)
        assert "membership_status" in fields
        assert user.membership_status == expected
        assert user.membership_status_changed_at is not None
        assert user.membership_status_changed_by == actor
        _assert_side_fields(user, status, event)

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "before_archive",
        [
            MembershipStatus.TENTATIVE,
            MembershipStatus.ACTIVE_MEMBER,
            MembershipStatus.ATTENDANCE_PAUSED,
            MembershipStatus.GUIDELINES_PAUSED,
            MembershipStatus.NONE,
            None,
        ],
    )
    @pytest.mark.parametrize(
        ("event", "fallback"),
        [
            (MembershipEvent.MARK_TENTATIVE, MembershipStatus.TENTATIVE),
            (MembershipEvent.APPROVE, MembershipStatus.ACTIVE_MEMBER),
        ],
    )
    def test_unarchive_events_restore_parked_pause_or_fallback(
        self, before_archive, event, fallback
    ):
        actor = _in_memory_user()
        user = _in_memory_user(archived=True, before_archive=before_archive)

        fields = _EVENT_CALLERS[event](user, actor)

        expected = before_archive if before_archive in PAUSED_STATUSES else fallback
        assert user.is_archived is False
        assert user.status_before_archive is None
        assert user.membership_status == expected
        assert user.membership_status_changed_by == actor
        assert "archived_at" in fields
        assert (user.attendance_paused_at is not None) == (
            expected == MembershipStatus.ATTENDANCE_PAUSED
        )

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "event",
        [
            MembershipEvent.PROMOTE_ON_CHECK_IN,
            MembershipEvent.RESTORE_ON_CHECK_IN,
            MembershipEvent.LIFT_ATTENDANCE_PAUSE,
            MembershipEvent.ARCHIVE,
        ],
    )
    def test_disallowed_events_on_archived_user_raise_without_mutating(self, event):
        actor = _in_memory_user()
        user = _in_memory_user(archived=True, before_archive=MembershipStatus.ATTENDANCE_PAUSED)
        before = _snapshot(user)

        with pytest.raises(InvalidStateTransition) as exc_info:
            _EVENT_CALLERS[event](user, actor)

        assert _snapshot(user) == before
        if event == MembershipEvent.ARCHIVE:
            assert exc_info.value.code == Code.User.ALREADY_ARCHIVED
        elif event == MembershipEvent.LIFT_ATTENDANCE_PAUSE:
            assert exc_info.value.code == Code.User.ATTENDANCE_PAUSE_LIFTS_ON_CHECK_IN

    @pytest.mark.unit
    def test_archived_pause_transitions_enforce_pause_rules(self):
        actor = _in_memory_user()
        archived_guidelines = _in_memory_user(
            archived=True, before_archive=MembershipStatus.GUIDELINES_PAUSED
        )
        with pytest.raises(InvalidStateTransition) as exc_info:
            archived_guidelines.apply_attendance_pause(by=actor)
        assert exc_info.value.code == Code.User.GUIDELINES_PAUSED
        assert archived_guidelines.status_before_archive == MembershipStatus.GUIDELINES_PAUSED

        archived_active = _in_memory_user(
            archived=True, before_archive=MembershipStatus.ACTIVE_MEMBER
        )
        with pytest.raises(InvalidStateTransition):
            archived_active.lift_guidelines_pause(by=actor)
        assert archived_active.status_before_archive == MembershipStatus.ACTIVE_MEMBER

        archived_none = _in_memory_user(archived=True, before_archive=MembershipStatus.NONE)
        with pytest.raises(InvalidStateTransition):
            archived_none.apply_guidelines_pause(by=actor)
        with pytest.raises(InvalidStateTransition):
            archived_none.apply_attendance_pause(by=actor)

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "event", [MembershipEvent.PAUSE_FOR_GUIDELINES, MembershipEvent.PAUSE_FOR_ATTENDANCE]
    )
    def test_archived_tentative_cannot_be_parked_into_a_pause(self, event):
        actor = _in_memory_user()
        user = _in_memory_user(archived=True, before_archive=MembershipStatus.TENTATIVE)
        before = _snapshot(user)

        with pytest.raises(InvalidStateTransition) as exc_info:
            _EVENT_CALLERS[event](user, actor)

        assert exc_info.value.code == Code.User.INVALID_STATUS_TRANSITION
        assert _snapshot(user) == before
        user.mark_tentative(by=actor)
        assert user.membership_status == MembershipStatus.TENTATIVE


@dataclass
class _ModelShadow:
    ever_left_none: bool = False


@settings(max_examples=75, stateful_step_count=25)
class MembershipStateMachineProperty(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.actor = _in_memory_user(MembershipStatus.ACTIVE_MEMBER)
        self.user = _in_memory_user(MembershipStatus.NONE)
        self.shadow = _ModelShadow()

    @initialize(
        initial=sampled_from(
            [MembershipStatus.NONE, MembershipStatus.TENTATIVE, MembershipStatus.ACTIVE_MEMBER]
        )
    )
    def init_user(self, initial: MembershipStatus):
        self.user = _in_memory_user(initial)
        self.shadow = _ModelShadow(ever_left_none=(initial != MembershipStatus.NONE))

    @rule(event=sampled_from(list(MembershipEvent)))
    def fire_event(self, event: MembershipEvent):
        was_guidelines = self.user.is_guidelines_paused
        before = _snapshot(self.user)
        try:
            _EVENT_CALLERS[event](self.user, self.actor)
        except InvalidStateTransition:
            assert _snapshot(self.user) == before
            return

        if self.user.membership_status != MembershipStatus.NONE:
            self.shadow.ever_left_none = True
        if was_guidelines and event != MembershipEvent.LIFT_GUIDELINES_PAUSE:
            assert self.user.is_guidelines_paused is True
        if was_guidelines and event == MembershipEvent.LIFT_GUIDELINES_PAUSE:
            assert self.user.membership_status != MembershipStatus.ACTIVE_MEMBER
            assert self.user.is_attendance_paused is True

    @invariant()
    def status_and_archive_invariants_hold(self):
        u = self.user
        assert (u.membership_status == MembershipStatus.ARCHIVED) == u.is_archived
        assert u.is_member == (u.membership_status in MEMBER_STATUSES)
        if u.is_archived:
            assert u.status_before_archive in MANAGED_STATUSES
        else:
            assert u.status_before_archive is None
            if u.membership_status == MembershipStatus.ATTENDANCE_PAUSED:
                assert u.attendance_paused_at is not None
            else:
                assert u.attendance_paused_at is None
        if self.shadow.ever_left_none:
            assert u.membership_status != MembershipStatus.NONE


TestMembershipStateful = pytest.mark.unit(MembershipStateMachineProperty.TestCase)


def _submit_and_promote(
    api_client, admin_user: User, admin_headers: dict, why_join_id: str
) -> User:
    sub = api_client.post(
        "/api/community/join-request/",
        {
            "first_name": "Journey",
            "last_name": "Member",
            "phone_number": "+14155550191",
            "email": "journey@example.com",
            "answers": {why_join_id: "solidarity"},
            "sms_consent": True,
            "guidelines_consent": True,
        },
        content_type="application/json",
    )
    assert sub.status_code == 201
    tent = api_client.patch(
        f"/api/community/join-requests/{sub.json()['id']}/",
        {"status": JoinRequestStatus.TENTATIVE},
        content_type="application/json",
        **admin_headers,
    )
    assert tent.status_code == 200
    member = User.objects.get(phone_number="+14155550191")
    assert member.membership_status == MembershipStatus.TENTATIVE
    _check_in_past_event(api_client, admin_user, member, EventType.OFFICIAL, 2)
    member.refresh_from_db()
    assert member.membership_status == MembershipStatus.ACTIVE_MEMBER
    return member


def _check_in_past_event(
    api_client, host: User, guest: User, event_type: EventType, hours_ago: int = 1
) -> None:
    ev = make_event(
        created_by=host,
        event_type=event_type,
        start_datetime=timezone.now() - timezone.timedelta(hours=hours_ago),
    )
    EventRSVP.objects.create(event=ev, user=guest, status=RSVPStatus.ATTENDING)
    resp = api_client.post(
        f"/api/community/events/{ev.id}/rsvps/{guest.pk}/attendance/",
        {"attendance": AttendanceStatus.ATTENDED},
        content_type="application/json",
        **auth_headers_for(host),
    )
    assert resp.status_code == 200


@pytest.mark.integration
class TestMembershipTransitionsEndToEnd:
    @pytest.mark.django_db(transaction=True, serialized_rollback=True)
    def test_full_user_lifecycle_and_rejected_transitions_persisted_in_audit_log(
        self, api_client, why_join_id
    ):
        admin_role, _ = Role.objects.get_or_create(name="admin", is_default=True)
        Role.objects.get_or_create(name="member", is_default=True)
        admin_user = make_user(
            PermissionKey.MANAGE_USERS,
            PermissionKey.APPROVE_JOIN_REQUESTS,
            PermissionKey.MANAGE_EVENTS,
            first_name="Boss",
        )
        admin_headers = auth_headers_for(admin_user)
        protected_admin = make_user(first_name="Protected")
        protected_admin.roles.add(admin_role)

        member = _submit_and_promote(api_client, admin_user, admin_headers, why_join_id)

        self_pause = api_client.patch(
            f"/api/auth/users/{admin_user.pk}/",
            {"guidelines_paused": True},
            content_type="application/json",
            **admin_headers,
        )
        assert_error_code(self_pause, Code.User.CANNOT_PAUSE_SELF)
        admin_pause = api_client.patch(
            f"/api/auth/users/{protected_admin.pk}/",
            {"attendance_paused": True},
            content_type="application/json",
            **admin_headers,
        )
        assert_error_code(admin_pause, Code.User.CANNOT_PAUSE_ADMIN)

        mcp_token = run_tool(
            admin_user, "set_attendance_pause", member_id=str(member.pk), paused=True
        )["confirm_token"]

        assert (
            api_client.patch(
                f"/api/auth/users/{member.pk}/",
                {"attendance_paused": True},
                content_type="application/json",
                **admin_headers,
            ).status_code
            == 200
        )
        bad_unpause = api_client.patch(
            f"/api/auth/users/{member.pk}/",
            {"attendance_paused": False},
            content_type="application/json",
            **admin_headers,
        )
        assert_error_code(bad_unpause, Code.User.ATTENDANCE_PAUSE_LIFTS_ON_CHECK_IN)

        assert (
            api_client.patch(
                f"/api/auth/users/{member.pk}/",
                {"guidelines_paused": True},
                content_type="application/json",
                **admin_headers,
            ).status_code
            == 200
        )
        err = tool_error(
            admin_user,
            "set_attendance_pause",
            member_id=str(member.pk),
            paused=True,
            confirm_token=mcp_token,
        )
        assert Code.User.GUIDELINES_PAUSED in err

        assert (
            api_client.patch(
                f"/api/auth/users/{member.pk}/",
                {"guidelines_paused": False},
                content_type="application/json",
                **admin_headers,
            ).status_code
            == 200
        )
        _check_in_past_event(api_client, admin_user, member, EventType.CLUB)
        member.refresh_from_db()
        assert member.membership_status == MembershipStatus.ACTIVE_MEMBER

        member.last_login = timezone.now()
        member.save(update_fields=["last_login"])
        assert (
            api_client.delete(f"/api/auth/users/{member.pk}/", **admin_headers).status_code == 204
        )
        arch_again = api_client.delete(f"/api/auth/users/{member.pk}/", **admin_headers)
        assert_error_code(arch_again, Code.User.ALREADY_ARCHIVED)

        member_logs = list(
            AuditLogEntry.objects.filter(
                target_type=AuditTargetType.USER, target_id=str(member.pk)
            ).order_by("created_at")
        )
        assert [e.action for e in member_logs] == [
            "user_marked_tentative",
            "user_promoted_on_check_in",
            "user_attendance_paused",
            "user_transition_rejected",
            "user_paused",
            "user_transition_rejected",
            "user_unpaused",
            "user_attendance_restored",
            "user_archived",
            "user_transition_rejected",
        ]
        assert member_logs[5].details["via"] == "mcp"
        assert member_logs[5].details["code"] == Code.User.GUIDELINES_PAUSED
        assert AuditLogEntry.objects.filter(
            action="user_transition_rejected", target_id=str(admin_user.pk)
        ).exists()
        assert AuditLogEntry.objects.filter(
            action="user_transition_rejected", target_id=str(protected_admin.pk)
        ).exists()
