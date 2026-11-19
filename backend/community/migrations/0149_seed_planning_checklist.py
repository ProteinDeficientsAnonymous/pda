from django.db import migrations

_QUESTIONNAIRE = """all are required, and each has one option, "yes", except the last:
- do you understand that your rsvp is not confirmed until you pay?
- do you understand that payments are not refundable for cancellations within 5 days of the event?
- do you understand that your payment is for your share of the group order and will not be returned to you?
- we repost content on ig that is critical of ice and supportive of palestine. we share group and candid photos from events. do you consent to being in photos on our ig (opt out is totally fine!)? options: "yes, i consent to being on the ig", "no, i'd like to opt out\""""

_ITEMS = [
    ("secure venue", ""),
    ("update event page with food (or venue) pic and restaurant info", ""),
    (
        "set the event type as official (pda-organized)",
        "if you don't see that option, tell leah so she can give you the permissions for it",
    ),
    (
        "if active meetup, update partiful with google maps route link and any other important info (like meetup location)",
        "make sure that event location is a pin of the start point",
    ),
    ("add the questionnaire to the partiful", _QUESTIONNAIRE),
    ("ask for facilitators in the event facilitator chat", ""),
    ("send out a reminder the day before the event", ""),
    (
        "after the meetup, send a message in chitty chat with the group pics thanking people for coming",
        "",
    ),
]


def seed_items(apps, schema_editor):
    PlanningChecklistItem = apps.get_model("community", "PlanningChecklistItem")
    if PlanningChecklistItem.objects.exists():
        return
    PlanningChecklistItem.objects.bulk_create(
        PlanningChecklistItem(text=text, detail=detail, order=order)
        for order, (text, detail) in enumerate(_ITEMS, 1)
    )


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0148_planning_checklist"),
    ]

    operations = [
        migrations.RunPython(seed_items, migrations.RunPython.noop),
    ]
