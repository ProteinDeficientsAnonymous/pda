from typing import Any

from asgiref.sync import sync_to_async
from community.models import Event, EventRSVP, EventStatus, RSVPStatus
from community.models.event_slug import event_lookup_q
from community.rsvps.answers import can_see_guest_questionnaire_responses
from mcp.server.mcpserver.exceptions import ToolError
from users.helpers import visible_display_name
from users.models import User

from mcp_gateway.server import FORBIDDEN, current_user, pda_tool
from mcp_gateway.tools.events_write import EventRef


def _snapshots(rsvp: EventRSVP) -> dict[str, dict[str, Any]]:
    stored = rsvp.questionnaire_responses or {}
    return {qid: snap for qid, snap in stored.items() if isinstance(snap, dict)}


def _removed_questions(rsvps: list[EventRSVP], current_ids: set[str]) -> list[dict[str, Any]]:
    labels: dict[str, str] = {}
    for rsvp in rsvps:
        for qid, snap in _snapshots(rsvp).items():
            if qid not in current_ids:
                labels.setdefault(qid, str(snap.get("label", qid)))
    # jsonb doesn't keep key order, so sort for a stable result
    ordered = sorted(labels.items(), key=lambda kv: (kv[1], kv[0]))
    return [{"id": qid, "label": label, "removed": True} for qid, label in ordered]


def _response(rsvp: EventRSVP, viewer: User) -> dict[str, Any]:
    return {
        "user_id": str(rsvp.user_id),
        "name": visible_display_name(rsvp.user, viewer),
        "is_member": rsvp.user.is_member,
        "status": rsvp.status,
        "answers": {qid: snap.get("answer") for qid, snap in _snapshots(rsvp).items()},
    }


def questionnaire_responses(user: User, event_ref: str) -> dict[str, Any]:
    event = (
        Event.objects.filter(event_lookup_q(event_ref))
        .exclude(status=EventStatus.DELETED)
        .select_related("created_by")
        .prefetch_related("co_hosts", "rsvp_questions")
        .first()
    )
    if event is None:
        raise ToolError("no event with that id or slug")
    co_host_ids = {str(u.id) for u in event.co_hosts.all()}
    if not can_see_guest_questionnaire_responses(user, event.created_by, co_host_ids):
        raise ToolError(FORBIDDEN)
    questions = list(event.rsvp_questions.all())
    rsvps = list(event.rsvps.exclude(status=RSVPStatus.REMOVED).select_related("user"))
    current = [
        {
            "id": str(q.id),
            "label": q.label,
            "field_type": q.field_type,
            "options": q.options,
            "required": q.required,
        }
        for q in questions
    ]
    return {
        "event": {"id": str(event.id), "slug": event.slug, "title": event.title},
        "questions": current + _removed_questions(rsvps, {q["id"] for q in current}),
        "responses": [_response(r, user) for r in rsvps],
    }


@pda_tool(
    description=(
        "read every guest's answers to an event's rsvp questionnaire (e.g. who opted out of "
        "photos). each guest's answers map question id to answer; look ids up in questions. "
        "deleted questions that still have answers are listed last with removed: true. labels "
        "can repeat, so match on id. only the event's host, co-hosts, or members who can manage "
        "events can use it. removed guests are left out; filter by status yourself."
    )
)
async def event_questionnaire_responses(
    event: EventRef,
) -> dict[str, Any]:
    return await sync_to_async(questionnaire_responses)(await current_user(), event)
