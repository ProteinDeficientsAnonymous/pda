import hashlib
import hmac
from collections import defaultdict
from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone

from audit.models import AuditLogEntry, AuditTargetType

# Persisted audit actions that mean someone hit a wall. Logger-only failures live in app logs.
FAILURE_ACTIONS = (
    "check_in_promotion_failed",
    "event_invite_email_failed",
    "join_request_transition_rejected",
    "login_failed",
    "magic_link_email_failed",
    "magic_login_failed",
    "mcp_connection_denied",
    "member_rsvp_email_failed",
    "password_change_failed",
    "permission_denied",
    "public_rsvp_cooldown_cache_error",
    "public_rsvp_email_collision",
    "public_rsvp_email_failed",
    "public_rsvp_recognized_email_failed",
    "public_rsvp_rejected_applicant_blocked",
    "public_rsvp_resend_email_failed",
    "rsvp_failed",
    "user_transition_rejected",
)
SUCCESS_ACTIONS = (
    "login_success",
    "magic_login_success",
    "password_changed",
    "public_rsvp_created",
    "public_rsvp_updated",
    "rsvp_changed",
)
CLUSTER_MIN = 3
CLUSTER_SPAN = timedelta(hours=1)
SAMPLES_PER_ACTION = 3
MAX_ROWS = 5000
_FIELDS = ("action", "created_at", "actor_id", "actor_label", "target_type", "target_id")


def ip_hash(ip: str | None) -> str | None:
    if not ip:
        return None
    return hmac.new(settings.SECRET_KEY.encode(), ip.encode(), hashlib.sha256).hexdigest()[:10]


def _member(row: dict) -> str | None:
    if user_id := (row["details"] or {}).get("user_id"):
        return str(user_id)
    if row["target_type"] == AuditTargetType.USER and row["target_id"]:
        return row["target_id"]
    return str(row["actor_id"]) if row["actor_id"] else None


def _rows(actions, since: datetime, until: datetime) -> list[dict]:
    qs = AuditLogEntry.objects.filter(
        action__in=actions, created_at__gte=since, created_at__lt=until
    ).order_by("created_at")
    rows = list(qs.values(*_FIELDS, "details", "ip_address")[:MAX_ROWS])
    for row in rows:
        row["member_id"] = _member(row)
        row["ip"] = ip_hash(row.pop("ip_address"))
    return rows


def _sample(row: dict) -> dict:
    keys = ("created_at", "actor_label", "target_type", "target_id", "details", "member_id", "ip")
    return {k: row[k] for k in keys}


def _group(rows: list[dict], key: str) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row[key]:
            grouped[row[key]].append(row)
    return grouped


def _by_action(failures: list[dict]) -> list[dict]:
    return sorted(
        (
            {
                "action": action,
                "count": len(rows),
                "first_seen": rows[0]["created_at"],
                "last_seen": rows[-1]["created_at"],
                "members": sorted({r["member_id"] for r in rows if r["member_id"]}),
                "samples": [_sample(r) for r in rows[-SAMPLES_PER_ACTION:]],
            }
            for action, rows in _group(failures, "action").items()
        ),
        key=lambda group: -group["count"],
    )


def _bursts(rows: list[dict]):
    start = 0
    while start < len(rows):
        end = start
        while (
            end < len(rows) and rows[end]["created_at"] - rows[start]["created_at"] <= CLUSTER_SPAN
        ):
            end += 1
        if end - start >= CLUSTER_MIN:
            yield rows[start:end]
            start = end
        else:
            start += 1


def _cluster(key: str, value: str, burst: list[dict], successes: list[dict]) -> dict:
    last = burst[-1]["created_at"]
    recovered = (s["created_at"] for s in successes if s[key] == value and s["created_at"] > last)
    return {
        key: value,
        "failures": len(burst),
        "actions": sorted({r["action"] for r in burst}),
        "first_seen": burst[0]["created_at"],
        "last_seen": last,
        "recovered_at": next(recovered, None),
    }


def _clusters(failures: list[dict], successes: list[dict]) -> list[dict]:
    clusters = [
        _cluster(key, value, burst, successes)
        for key in ("member_id", "ip")
        for value, rows in _group(failures, key).items()
        for burst in _bursts(rows)
    ]
    return sorted(clusters, key=lambda c: c["first_seen"])


def trouble_report(since: datetime, until: datetime | None = None) -> dict:
    until = until or timezone.now()
    failures = _rows(FAILURE_ACTIONS, since, until)
    successes = _rows(SUCCESS_ACTIONS, since, until)
    return {
        "actions": _by_action(failures),
        "clusters": _clusters(failures, successes),
        "truncated": len(failures) >= MAX_ROWS,
    }
