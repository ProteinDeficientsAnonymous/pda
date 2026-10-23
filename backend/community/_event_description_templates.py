from config.auth import gated_jwt
from ninja import Router
from ninja.responses import Status
from pydantic import BaseModel

router = Router()

OFFICIAL_WALK_TEMPLATE = """Come join us on a walk _______where?_______!

Price includes ____what food are we ordering per person?___

We'll walk ___where?__________ and then head to _________________!

The route will be just about _______ miles and we'll walk at a social pace.

Only vegans allowed 🌱

Meetup at _____location______ at ____time____, we'll start walking at _____time (15min later than meet time)_____

This will be the route:
_________google maps route link________

We'll share our location in the WhatsApp community when we start; please DM a host if you need access

The price for this event is your share for the group order and will not be returned to you. No refunds will be issued for cancellations within 5 days of the event - if there is leftover money it will go towards PDA ops, a fund to assist low income friends, and a coffee for our event planners / facilitators.

Disclaimer:
Your physical safety is your responsibility. We will do all we can to be safe, but we are not liable for any injury or harm that comes to you. It's your responsibility to know and communicate as necessary your physical limitations

We take group photos at events and share them to instagram - if you don't want your photo shared please let us know in advance or during the event 💞🌱

Check us out on IG @protein.deficients.anonymous!"""

OFFICIAL_NON_WALK_TEMPLATE = """Another meetup of Protein Deficients Anonymous!

if there is a price: Price includes ____what food are we ordering per person?___

Only vegans allowed 🌱

Please be sure to rsvp so we can get an accurate count for the restaurant, and to stay in the loop about updates!

The price for this event is your share for the group order and will not be returned to you. No refunds will be issued for cancellations within 5 days of the event - if there is leftover money it will go towards PDA ops, a fund to assist low income friends, and a coffee for our event planners / facilitators.

We take group photos at events and share them to instagram - if you don't want your photo shared please let us know in advance or during the event 💞🌱

Check us out on IG @protein.deficients.anonymous! DM us to be added to the Whatsapp community"""


class EventDescriptionTemplatesOut(BaseModel):
    official_walk: str
    official_non_walk: str


@router.get(
    "/event-description-templates/",
    response={200: EventDescriptionTemplatesOut},
    auth=gated_jwt,
)
def get_event_description_templates(request):
    return Status(
        200,
        EventDescriptionTemplatesOut(
            official_walk=OFFICIAL_WALK_TEMPLATE,
            official_non_walk=OFFICIAL_NON_WALK_TEMPLATE,
        ),
    )
