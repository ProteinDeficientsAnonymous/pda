from config.auth import gated_jwt
from ninja import Router
from ninja.responses import Status
from pydantic import BaseModel

router = Router()

OFFICIAL_WALK_TEMPLATE = """Come join us on a walk around [neighborhood / park]!

Price includes [what we're ordering, per person].

We'll walk [route, e.g. along the river] and then head to [end spot]!

The route is about [X] miles and we'll walk at a social pace.

Only vegans allowed 🌱

Meet up at [meeting spot] at [meet time]. We'll start walking at [start time, 15 min after meet time].

Route: [google maps link]

We'll share our location in the WhatsApp community when we start. Please DM a host if you need access.

The price for this event is your share of the group order and will not be returned to you. No refunds will be issued for cancellations within 5 days of the event. Any leftover money goes towards PDA ops, a fund to assist low-income friends, and a coffee for our event planners / facilitators.

Disclaimer: your physical safety is your responsibility. We will do all we can to be safe, but we are not liable for any injury or harm that comes to you. It's your responsibility to know your physical limitations and communicate them as needed.

We take group photos at events and share them on Instagram. If you don't want your photo shared, please let us know in advance or during the event 💞🌱

Check us out on IG @protein.deficients.anonymous!"""

OFFICIAL_NON_WALK_TEMPLATE = """Another meetup of Protein Deficients Anonymous!

Price includes [what we're ordering, per person]. [delete this line and the refund note below if the event is free]

Only vegans allowed 🌱

Please be sure to RSVP so we can get an accurate count for the restaurant, and to stay in the loop about updates!

The price for this event is your share of the group order and will not be returned to you. No refunds will be issued for cancellations within 5 days of the event. Any leftover money goes towards PDA ops, a fund to assist low-income friends, and a coffee for our event planners / facilitators.

We take group photos at events and share them on Instagram. If you don't want your photo shared, please let us know in advance or during the event 💞🌱

Check us out on IG @protein.deficients.anonymous! DM us to be added to the WhatsApp community."""


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
