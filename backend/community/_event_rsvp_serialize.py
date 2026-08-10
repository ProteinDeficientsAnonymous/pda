from community._event_schemas import EventRsvpQuestionOut
from community.models import EventRsvpQuestion


def event_rsvp_question_out(question: EventRsvpQuestion) -> EventRsvpQuestionOut:
    return EventRsvpQuestionOut(
        id=str(question.id),
        label=question.label,
        field_type=question.field_type,
        options=list(question.options or []),
        required=question.required,
        display_order=question.display_order,
    )
