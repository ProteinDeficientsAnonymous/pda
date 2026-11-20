import ast
from collections.abc import Iterator
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
# The only modules allowed to write state fields; everything else fires a model event method.
TRANSITION_MODULES = frozenset(
    {
        BACKEND / "users" / "_transitions.py",
        BACKEND / "community" / "models" / "_join_request_transitions.py",
    }
)
SKIP_DIRS = frozenset({"tests", "migrations", ".venv", "__pycache__", "node_modules"})
USER_STATE_FIELDS = frozenset({"membership_status", "status_before_archive", "archived_at"})
JOIN_REQUEST_STATUS_ENUM = "JoinRequestStatus"
BULK_WRITE_METHODS = frozenset({"update", "bulk_update"})


def _mentions_join_request_status(node: ast.AST) -> bool:
    return any(isinstance(n, ast.Name) and n.id == JOIN_REQUEST_STATUS_ENUM for n in ast.walk(node))


def _is_join_request_receiver(node: ast.AST) -> bool:
    for n in ast.walk(node):
        if isinstance(n, ast.Name) and (
            n.id == "JoinRequest" or n.id == "jr" or "join_request" in n.id
        ):
            return True
        if isinstance(n, ast.Attribute) and "join_request" in n.attr:
            return True
    return False


def _is_join_request_status_write(receiver: ast.AST, value: ast.AST | None) -> bool:
    if value is not None and _mentions_join_request_status(value):
        return True
    return _is_join_request_receiver(receiver)


def _guarded_store_attr(target: ast.AST, value: ast.AST | None) -> str | None:
    if not isinstance(target, ast.Attribute):
        return None
    if target.attr in USER_STATE_FIELDS:
        return target.attr
    if target.attr == "status" and _is_join_request_status_write(target.value, value):
        return target.attr
    return None


def _assignment_hits(node: ast.AST) -> Iterator[str]:
    if isinstance(node, ast.Assign):
        stores = [(leaf, node.value) for t in node.targets for leaf in ast.walk(t)]
    elif isinstance(node, ast.AugAssign | ast.AnnAssign):
        stores = [(node.target, node.value)]
    else:
        return
    for target, value in stores:
        attr = _guarded_store_attr(target, value)
        if attr:
            yield f"assigns .{attr}"


def _bulk_write_fields(receiver: ast.AST, call: ast.Call) -> set[str]:
    fields: set[str] = set()
    for kw in call.keywords:
        if kw.arg in USER_STATE_FIELDS:
            fields.add(kw.arg)
        elif kw.arg == "status" and _is_join_request_status_write(receiver, kw.value):
            fields.add(kw.arg)
        elif kw.arg == "fields":
            fields |= {
                c.value
                for c in ast.walk(kw.value)
                if isinstance(c, ast.Constant)
                and isinstance(c.value, str)
                and c.value in USER_STATE_FIELDS
            }
    return fields


def _call_hits(node: ast.AST) -> Iterator[str]:
    if not isinstance(node, ast.Call):
        return
    func = node.func
    if isinstance(func, ast.Attribute) and func.attr in BULK_WRITE_METHODS:
        for field in sorted(_bulk_write_fields(func.value, node)):
            yield f".{func.attr}({field}=...)"
    if isinstance(func, ast.Name) and func.id == "setattr" and len(node.args) >= 2:
        name = node.args[1]
        if isinstance(name, ast.Constant) and name.value in USER_STATE_FIELDS:
            yield f"setattr(..., {name.value!r})"


def direct_state_writes(source: str) -> list[tuple[int, str]]:
    """Find state-field writes that bypass the transition methods.

    param(source): python source to scan
    return(list[tuple[int, str]]): (line, description) per offending write
    """
    hits: list[tuple[int, str]] = []
    for node in ast.walk(ast.parse(source)):
        for desc in (*_assignment_hits(node), *_call_hits(node)):
            hits.append((getattr(node, "lineno", 0), desc))
    return sorted(set(hits))


def _production_modules() -> Iterator[Path]:
    for path in BACKEND.rglob("*.py"):
        rel = path.relative_to(BACKEND).parts
        if SKIP_DIRS.intersection(rel) or path in TRANSITION_MODULES:
            continue
        yield path


@pytest.mark.unit
def test_no_direct_state_writes_outside_transition_modules():
    violations = [
        f"{path.relative_to(BACKEND)}:{line}: {desc}"
        for path in _production_modules()
        for line, desc in direct_state_writes(path.read_text())
    ]
    assert not violations, (
        "Change membership/join-request state through the model event methods "
        "(see .claude/rules/state-machines.md):\n" + "\n".join(violations)
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "source",
    [
        "user.membership_status = MembershipStatus.ACTIVE_MEMBER",
        "user.archived_at = timezone.now()",
        "u.status_before_archive: str = 'x'",
        "jr.status = JoinRequestStatus.CLOSED",
        "join_request.status = status",
        "self.join_request.status = new",
        "user.join_requests.filter(status='tentative').update(status=closed)",
        "JoinRequest.objects.filter(pk=1).update(status=target)",
        "a, user.membership_status = 1, 2",
        "User.objects.filter(pk=1).update(membership_status='none')",
        "JoinRequest.objects.filter(pk=1).update(status=JoinRequestStatus.CLOSED)",
        "User.objects.bulk_update(users, fields=['archived_at'])",
        "setattr(user, 'membership_status', 'none')",
    ],
)
def test_guard_flags_direct_writes(source):
    assert direct_state_writes(source)


@pytest.mark.unit
@pytest.mark.parametrize(
    "source",
    [
        "user.save(update_fields=user.approve_membership(by=actor))",
        "User.objects.create(membership_status=MembershipStatus.TENTATIVE)",
        "JoinRequest.objects.create(status=JoinRequestStatus.PENDING)",
        "rsvp.status = RSVPStatus.ATTENDING",
        "Event.objects.filter(pk=1).update(status=EventStatus.DRAFT)",
        "qs.filter(membership_status=MembershipStatus.NONE)",
        "x = user.membership_status",
    ],
)
def test_guard_allows_reads_creates_and_unrelated_status(source):
    assert direct_state_writes(source) == []
