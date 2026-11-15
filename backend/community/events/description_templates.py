from config.auth import gated_jwt
from ninja import Router
from ninja.responses import Status
from pydantic import BaseModel

router = Router()

HOW_TO_SHOW_UP = """How to show up at PDA events:
- Say hi to someone you don't know yet, and if you already know a lot of people, talk to newer folks and make them feel welcome
- Stay curious — ask questions and really listen to the answers
- If you're a cis man, and especially a white cis man, be mindful of the space you take up. Let people finish their thoughts before jumping in, notice if you're steering every conversation, and make room for others. If you see other men cutting people off, be the one to ask them to let others finish.
- If you're white, be mindful of your privilege and watch for microaggressions. If someone names one, thank them and listen rather than getting defensive or explaining yourself. If you see someone else make one, say something or let the facilitators know."""

OFFICIAL_WALK_TEMPLATE = f"""Come join us on a walk around [NEIGHBORHOOD / PARK]!

Price includes [WHAT WE'RE ORDERING, PER PERSON].

We'll walk [ROUTE, E.G. ALONG THE RIVER] and then head to [END SPOT]!

The route is about [X] miles and we'll walk at a social pace.

Only vegans allowed 🌱

Meet up at [MEETING SPOT] at [MEET TIME]. We'll start walking at [START TIME, 15 MIN AFTER MEET TIME].

Route: [GOOGLE MAPS LINK]

We'll share our location in the WhatsApp community when we start. Please DM a host if you need access.

The price for this event is your share of the group order and will not be returned to you. No refunds will be issued for cancellations within 5 days of the event. Any leftover money goes towards PDA ops, a fund to assist low-income friends, and a coffee for our event planners / facilitators.

Disclaimer: your physical safety is your responsibility. We will do all we can to be safe, but we are not liable for any injury or harm that comes to you. It's your responsibility to know your physical limitations and communicate them as needed.

{HOW_TO_SHOW_UP}

We take group photos at events and share them on Instagram. If you don't want your photo shared, please let us know in advance or during the event 💞🌱

Check us out on IG @protein.deficients.anonymous!"""

OFFICIAL_NON_WALK_TEMPLATE = f"""Another meetup of Protein Deficients Anonymous!

Price includes [WHAT WE'RE ORDERING, PER PERSON].

Only vegans allowed 🌱

Please be sure to RSVP so we can get an accurate count for the restaurant, and to stay in the loop about updates!

The price for this event is your share of the group order and will not be returned to you. No refunds will be issued for cancellations within 5 days of the event. Any leftover money goes towards PDA ops, a fund to assist low-income friends, and a coffee for our event planners / facilitators.

{HOW_TO_SHOW_UP}

We take group photos at events and share them on Instagram. If you don't want your photo shared, please let us know in advance or during the event 💞🌱

Check us out on IG @protein.deficients.anonymous! DM us to be added to the WhatsApp community."""

CLUB_TEMPLATE = HOW_TO_SHOW_UP


class EventDescriptionTemplatesOut(BaseModel):
    official_walk: str
    official_non_walk: str
    club: str


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
            club=CLUB_TEMPLATE,
        ),
    )
