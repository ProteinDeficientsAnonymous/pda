import json

from django.contrib.auth.models import AnonymousUser

from community.planning._access import require_manage, require_view
from community.validation import Code, raise_validation

GUIDELINES_SLUG = "planning-guidelines"

_SEED = [
    (
        "restaurant meetups",
        [
            "planning should be finalized at least a month out so that we can share it with the group",
            "we always go to fully vegan restaurants – part of the goal of these meetups is to support vegan businesses",
            "all official meetups are in nyc",
            "with current size, they need to be able to accommodate a group of 20-25",
            "some places will require a deposit – we can make that work",
            "ideally, they can accommodate everyone being on separate checks, though if that's not possible we can make it work",
            "target price is about $35-40 per person",
            "generally, we would do these in bk or manhattan (though this can be more difficult to find places that can accommodate a large group) but we can also do queens restaurants",
            "we generally want to find places we haven't been before, but of course eventually we'll have to repeat places",
            "current cadence is 1 per month",
            "no cityroots or other zionist affiliated restaurants",
            (
                "places we've been:",
                [
                    "sentir",
                    "beyond sushi",
                    "willow",
                    "anixi",
                    "coletta",
                    "le basque",
                    "reverie",
                    "planta",
                ],
            ),
        ],
    ),
    (
        "active meetups",
        [
            "planning should be finalized at least a month out so that we can share it with the group",
            "currently we either do bike rides or walks, though we could do other types (note that if we do runs, leah will not join so we need to get folks ramped up on planning before that)",
            "currently active meetups are generally 15-25 people",
            "active meetups should always end at food",
            "we only go to fully vegan spots",
            "more casual eateries for the active meetups",
            (
                "in the winter this is tough because we need to be indoors. current places we've found that work for cold weather are:",
                ["le petit monstre", "arts and crafts", "principles gi"],
            ),
            "we generally want to find places we haven't been before, but of course eventually we'll have to repeat places (especially in the wintertime)",
            "all activities are done at a social pace – this means slow and taking pretty frequent breaks",
            (
                "bike rides",
                [
                    "citibike friendly",
                    "3-4 stops for water and citibike refresh",
                    "target is like 10ish miles",
                    "paused in winter for cold weather",
                ],
            ),
            (
                "walks",
                [
                    "take breaks as needed",
                    "target ~1hr according to google (~1 1/2 hrs at a social pace) or about 3mi",
                ],
            ),
            "meetups should not involve taking public transit",
            "time on streets for biking and walks should be limited – preference for more time within parks",
            "follow all traffic rules – only cross the street when you have the walk sign; wait if the group gets split up; if on bikes, yield to pedestrians",
            "share your location in the whatsapp in case some people are late and need to catch up, or in case someone loses the group somehow",
            "partiful event should list meetup time and rollout time or walking start time",
            "don't wait a long time beyond rollout time or walking start time – take as much time as you need for intros and then go",
            "there should always be 1 delegated front person and 1 delegated back person – the group should not get far ahead of the front person, no one should be behind the back person",
            "current cadence is 1 per month",
        ],
    ),
    (
        "hosting",
        [
            "make a flyer for ig (i typically use canva)",
            "you will need to send out a few updates leading up to the event for people to update rsvps if plans changed",
            "once the event gets waitlisted, text blast maybes to let them know that a maybe doesn't get them a spot at the event and they'll need to join the waitlist",
            "reach out to the restaurant the week of (and possibly day of in some cases) to remind them that we're coming",
            "arrive early! you should be the first person there – in some cases you'll need to set up tables, in others just be there so people don't feel lost when they arrive (especially new people)",
            "at the event, lead introductions and icebreaker",
            "ask couples and close friends to split up",
            "make sure that if you see someone who is isolated or not talking that you invite them into convo",
            "mix up the group halfway through sitting so that people get a chance to talk to others",
            "during active meetups, share your location in the whatsapp in case some people are late and need to catch up, or in case someone loses the group somehow",
            "i always put lil fruit / veggie emojis when people mark that they're going. i think this is very cute and sweet and i encourage you to keep up the tradition or make your own play on it!",
        ],
    ),
]


def _paragraph(text: str) -> dict:
    return {"type": "paragraph", "content": [{"type": "text", "text": text}]}


def _bullets(items: list) -> dict:
    nodes = []
    for item in items:
        if isinstance(item, tuple):
            text, children = item
            nodes.append({"type": "listItem", "content": [_paragraph(text), _bullets(children)]})
        else:
            nodes.append({"type": "listItem", "content": [_paragraph(item)]})
    return {"type": "bulletList", "content": nodes}


def seed_doc() -> str:
    content = []
    for heading, items in _SEED:
        content.append(
            {
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": heading}],
            }
        )
        content.append(_bullets(items))
    return json.dumps({"type": "doc", "content": content})


def require_guidelines_view(request) -> None:
    if isinstance(request.auth, AnonymousUser):
        raise_validation(Code.Page.MEMBERS_ONLY, status_code=403)
    require_view(request, "get_planning_guidelines")


def require_guidelines_edit(request, action: str = "update_planning_guidelines") -> None:
    require_manage(request, action)
