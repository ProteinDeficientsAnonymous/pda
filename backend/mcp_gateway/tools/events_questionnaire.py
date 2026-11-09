from typing import Annotated, Any

from asgiref.sync import sync_to_async
from community.models import Event, EventRSVP, RSVPStatus
from community.models.event_slug import event_lookup_q
from community.rsvps.answers import can_see_guest_questionnaire_responses
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field
from users.helpers import visible_display_name
from users.models import User

from mcp_gateway.server import FORBIDDEN, current_user, pda_tool


def _response(rsvp: EventRSVP, labels: dict[str, str], viewer: User) -> dict[str, Any]:
    answers = rsvp.questionnaire_responses or {}
    return {
        "user_id": str(rsvp.user_id),
        "name": visible_display_name(rsvp.user, viewer),
        "is_member": rsvp.user.is_member,
        "status": rsvp.status,
        "answers": {label: answers[qid] for qid, label in labels.items() if qid in answers},
    }


def questionnaire_responses(user: User, event_ref: str) -> dict[str, Any]:
    event = (
        Event.objects.filter(event_lookup_q(event_ref), deleted_at__isnull=True)
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
    labels = {str(q.id): q.label for q in questions}
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
        "responses": [_response(r, labels, user) for r in rsvps],
    }


@pda_tool(
    description=(
        "read every guest's answers to an event's rsvp questionnaire (e.g. who opted out of "
        "photos), keyed by question label. only the event's host, co-hosts, or members who can "
        "manage events can use it. removed guests are left out; filter by status yourself."
    )
)
async def event_questionnaire_responses(
    event: Annotated[str, Field(description="event id (uuid) or slug, e.g. from list_my_events")],
) -> dict[str, Any]:
    return await sync_to_async(questionnaire_responses)(await current_user(), event)
