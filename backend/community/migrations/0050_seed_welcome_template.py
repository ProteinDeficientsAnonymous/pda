from django.db import migrations

DEFAULT_BODY = """Hi, ${NAME}! I’m ${SENDER_NAME}, part of the vetting team at PDA (Protein Deficient Anonymous). We’re excited to have you!

Just to give you a little rundown: this newly-launched website hosts our PDA community events calendar, while conversations and announcements are in our WhatsApp group. We add people to the group in a batch in the late morning - when you join, I’ll welcome you and direct you to the intros channel, where you can drop a lil' introduction about yourself. Things people tend to share are how long they’ve been vegan, what their hobbies are (sometimes you find connections to others in the group based on that), their jobs, but you can share whatever you like!


Here are a couple of things to know about our WhatsApp community:
There is only 1 group in the community that is NOT for chatting: Side Quests and Hangouts. Please take a look at the guidelines in the group info for that group before posting in there (and posting in there IS encouraged).

All of the other groups ARE made for chatting! *If it ever feels too chatty or you’re overwhelmed with notifications, you can absolutely mute Chitty Chat (or any other group), or even leave it entirely.* There is a link to community guidelines and a link to a feedback survey that is permanently open in the community info on WhatsApp.

A big welcome to you, and I hope you enjoy PDA!

You can go ahead and use this link to sign into the website:
${MAGIC_LINK}"""


def seed_template(apps, schema_editor):
    WelcomeMessageTemplate = apps.get_model("community", "WelcomeMessageTemplate")
    WelcomeMessageTemplate.objects.update_or_create(pk=1, defaults={"body": DEFAULT_BODY})


def unseed_template(apps, schema_editor):
    WelcomeMessageTemplate = apps.get_model("community", "WelcomeMessageTemplate")
    WelcomeMessageTemplate.objects.filter(pk=1).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0049_welcomemessagetemplate"),
    ]

    operations = [
        migrations.RunPython(seed_template, unseed_template),
    ]
