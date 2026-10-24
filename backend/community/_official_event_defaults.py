from config.auth import gated_jwt
from ninja import Router
from ninja.responses import Status
from pydantic import BaseModel

from community._event_schemas import EventRsvpQuestionIn
from community.models import RsvpQuestionType

router = Router()

OFFICIAL_CASHAPP_LINK = "https://cash.app/$pdanyc"

_YES = ["Yes"]

OFFICIAL_RSVP_QUESTIONS = [
    EventRsvpQuestionIn(
        label="Do you understand that your RSVP is not confirmed until you pay?",
        field_type=RsvpQuestionType.SELECT,
        options=_YES,
        required=True,
    ),
    EventRsvpQuestionIn(
        label=(
            "Do you understand that payments are not refundable for cancellations"
            " within 5 days of the event?"
        ),
        field_type=RsvpQuestionType.SELECT,
        options=_YES,
        required=True,
    ),
    EventRsvpQuestionIn(
        label=(
            "Do you understand that your payment is for your share of the group order"
            " and will not be returned to you?"
        ),
        field_type=RsvpQuestionType.SELECT,
        options=_YES,
        required=True,
    ),
    EventRsvpQuestionIn(
        label=(
            "We repost content on IG that is critical of ICE and supportive of Palestine."
            " We share group and candid photos from events. Do you consent to being in"
            " photos on our IG (opt out is totally fine!)?"
        ),
        field_type=RsvpQuestionType.SELECT,
        options=["Yes, I consent to being on the IG", "No, I'd like to opt out"],
        required=True,
    ),
]


class OfficialEventDefaultsOut(BaseModel):
    cashapp_link: str
    rsvp_questions: list[EventRsvpQuestionIn]


@router.get(
    "/official-event-defaults/",
    response={200: OfficialEventDefaultsOut},
    auth=gated_jwt,
)
def get_official_event_defaults(request):
    return Status(
        200,
        OfficialEventDefaultsOut(
            cashapp_link=OFFICIAL_CASHAPP_LINK, rsvp_questions=OFFICIAL_RSVP_QUESTIONS
        ),
    )
