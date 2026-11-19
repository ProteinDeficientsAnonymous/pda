import json

DEFAULT_OPEN_ROLES = [
    "whatsapp moderators (our biggest need at the moment)",
    "someone to send out announcements",
    "event facilitators and planners",
]


def t(text: str, bold: bool = False) -> dict:
    node: dict = {"type": "text", "text": text}
    if bold:
        node["marks"] = [{"type": "bold"}]
    return node


def blank(key: str) -> dict:
    return {"type": "speechBlank", "attrs": {"key": key}}


def p(*inline: dict | str) -> dict:
    return {"type": "paragraph", "content": [t(i) if isinstance(i, str) else i for i in inline]}


def h(text: str) -> dict:
    return {"type": "heading", "attrs": {"level": 3}, "content": [t(text)]}


def note(*inline: dict | str) -> dict:
    return {"type": "blockquote", "content": [p(*inline)]}


def ul(*items: tuple[dict | str, ...]) -> dict:
    return {
        "type": "bulletList",
        "content": [{"type": "listItem", "content": [p(*item)]} for item in items],
    }


def _doc(*blocks: dict) -> dict:
    return {"type": "doc", "content": list(blocks)}


def _shared_doc() -> dict:
    return _doc(
        note("do this speech before intros so that if people come late they don't miss intros"),
        p(
            "PDA is all about connection and community. We believe that connection and community "
            "are so important, especially within the vegan community since so many vegans feel "
            "isolated from other vegans. We structure our meetups to be geared towards "
            "connection. We have several facilitators who will be at different section of the "
            "group today. Today our facilitators are ",
            blank("facilitators"),
            ".",
        ),
        note("point out facilitators"),
        p(
            "Facilitators are here to keep us on track but also to make sure that people are "
            "engaged and we're all getting the most we can out of this gathering. We always ask "
            "couples to separate at our events, so if you're still with your partner, please "
            "split up so you can have the opportunity to meet new people!"
        ),
        p(
            "We also have a whatsapp community where we have lots of clubs that meet monthly. "
            "Also, anyone can post a side quest or hangout, and we encourage you to meet up with "
            "each other outside of the official events!"
        ),
        p(
            "As a collective, PDA's stance is anti-oppression and pro-liberation for animals and "
            "also for humans. You already told us if you consent to being in photos on our IG "
            "when you RSVP'd but we want to give you another chance to opt in or out. We repost "
            "content on IG that is critical of ICE and supportive of Palestine. We know some "
            "folks have immigration concerns. If you cant or dont want to be in our group photo "
            "for instagram, that is totally fine with us! we take both group photos and candid "
            "photos. we'll ask you to step out of the group photo while we take the first one for "
            "ig and then come back in to take one not for ig. If you decided to opt out today but "
            "didnt tell us on your RSVP, please also tell a facilitator so we know not to post "
            "candid photos of you."
        ),
        h("PDA updates"),
        p(
            "PDA is entirely community run! We are all people who love being in this lil vegan "
            "community. We would love for people to join us in running it! We've got lots of ways "
            "you can help, but here are a few roles we especially need help with right now:"
        ),
        p(blank("open_roles")),
        h("Events update"),
        p(blank("upcoming_events")),
        p("Note: we dont make money off events, what we charge you is what it costs!"),
    )


def _walk_doc() -> dict:
    return _doc(
        h("Walk stuff"),
        ul(
            (
                "We'll walk at a social pace – social means SLOW. ",
                blank("front_walker"),
                " will be in front and ",
                blank("back_walker"),
                " will be in the back. Don't go too far ahead of the front person and try not to "
                "get too far behind the back person (though they should be looking for you).",
            ),
            (
                "Whenever we get to streets, we'll walk 2x2 so that we dont take up the whole "
                "sidewalk and so we can stay together. Please make sure to stay 2x2 when we're "
                "walking on the street! We'll stop before this to give you a heads up.",
            ),
            (
                "We'll take breaks as needed! If anyone needs a bio break, please let one of the "
                "facilitators know so we can stop at the nearest bathroom. We'll also take a "
                "break to get a group photo!",
            ),
            (blank("walk_details"),),
        ),
        p(
            t("Intros", bold=True),
            ": name, pronouns, ",
            blank("intro_question"),
            ", name once more",
        ),
        h("Start the walk"),
        ul(
            (
                "If you came here with your partner please separate! We want you to get a chance "
                "to talk to new people! If you already know a lot of people here please try to "
                "talk to new people as well.",
            ),
            (
                "Let's count off! We will count off again at some point during the walk to make "
                "sure we still have everyone so remember your number!",
            ),
        ),
        note(
            "count off (each person says their own number around the circle), then start the walk"
        ),
    )


def _restaurant_doc() -> dict:
    return _doc(
        h("Restaurant stuff"),
        p(
            "A reminder that the buffet is included but any drinks you order will be extra and "
            "you'll order and pay for those separately!"
        ),
        p(
            "About halfway through we'll prompt you to shuffle and mix up who you're talking "
            "to! It will be a little chaotic but i promise at the end you'll all have someone "
            "new to talk to and it'll work out!"
        ),
        p(
            "Let's give a big thank you to ",
            blank("restaurant"),
            " for having us! Now let's take our group photos!",
        ),
        note("take the pics and then encourage everyone to meet new friends"),
        note(
            "facilitators can lead intros (name, pronouns, ",
            blank("intro_question"),
            ", name once more)",
        ),
        note(
            "when you do the shuffle, remind them again that it'll be chaotic but the dust "
            "will settle and it'll all work out"
        ),
    )


def default_template_docs() -> tuple[dict, dict, dict]:
    """return(tuple): shared, walk and restaurant ProseMirror docs."""
    return _shared_doc(), _walk_doc(), _restaurant_doc()


def seed_default_template(template_model) -> None:
    """Fill the singleton with the default docs, only when none of its three docs has content."""
    template, _ = template_model.objects.get_or_create(pk=1)
    docs = (template.shared_pm, template.walk_pm, template.restaurant_pm)
    if any(d and d.strip() for d in docs):
        return
    shared, walk, restaurant = default_template_docs()
    template.shared_pm = json.dumps(shared)
    template.walk_pm = json.dumps(walk)
    template.restaurant_pm = json.dumps(restaurant)
    if not template.open_roles:
        template.open_roles = list(DEFAULT_OPEN_ROLES)
    template.save()
