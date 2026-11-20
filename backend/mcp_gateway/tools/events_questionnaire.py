from typing import Any

from asgiref.sync import sync_to_async
from community.models import Event, EventRSVP, EventRsvpQuestion, EventStatus, RSVPStatus
from community.models.event_slug import event_lookup_q
from community.rsvps.answers import can_see_guest_questionnaire_responses
from mcp.server.mcpserver.exceptions import ToolError
from users.helpers import visible_display_name
from users.models import User

from mcp_gateway.server import FORBIDDEN, current_user, pda_tool
from mcp_gateway.tools.events_write import EventRef


def _answers(rsvp: EventRSVP, questions: list[EventRsvpQuestion]) -> list[dict[str, Any]]:
    stored = rsvp.questionnaire_responses or {}
    snaps = {qid: snap for qid, snap in stored.items() if isinstance(snap, dict)}
    answers: list[dict[str, Any]] = [
        {"question": q.label, "answer": snaps.pop(str(q.id)).get("answer")}
        for q in questions
        if str(q.id) in snaps
    ]
    # jsonb doesn't keep key order, so sort leftovers for a stable result
    for qid, snap in sorted(snaps.items(), key=lambda kv: (str(kv[1].get("label", kv[0])), kv[0])):
        label = snap.get("label", qid)
        answers.append({"question": label, "answer": snap.get("answer"), "removed": True})
    return answers


def _response(rsvp: EventRSVP, questions: list[EventRsvpQuestion], viewer: User) -> dict[str, Any]:
    return {
        "user_id": str(rsvp.user_id),
        "name": visible_display_name(rsvp.user, viewer),
        "is_member": rsvp.user.is_member,
        "status": rsvp.status,
        "answers": _answers(rsvp, questions),
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
    rsvps = event.rsvps.exclude(status=RSVPStatus.REMOVED).select_related("user")
    return {
        "event": {"id": str(event.id), "slug": event.slug, "title": event.title},
        "questions": [
            {
                "label": q.label,
                "field_type": q.field_type,
                "options": q.options,
                "required": q.required,
            }
            for q in questions
        ],
        "responses": [_response(r, questions, user) for r in rsvps],
    }


@pda_tool(
    description=(
        "read every guest's answers to an event's rsvp questionnaire (e.g. who opted out of "
        "photos). each guest's answers are a list of {question, answer} in question order; "
        "answers to deleted questions come last with removed: true. labels can repeat. only the "
        "event's host, co-hosts, or members who can manage events can use it. removed guests "
        "are left out; filter by status yourself."
    )
)
async def event_questionnaire_responses(
    event: EventRef,
) -> dict[str, Any]:
    return await sync_to_async(questionnaire_responses)(await current_user(), event)
