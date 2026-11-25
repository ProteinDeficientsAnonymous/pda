import re

from django.db import migrations

CLUBS_QUESTION_ID = "266d97e3-56c9-4edc-805e-85a234cc58f9"
_OPTION_RE = re.compile(r"^(?P<name>.*?)\s*\((?P<requirements>.*)\)$")


def _parse_option(option: str) -> tuple[str, str]:
    match = _OPTION_RE.match(option.strip())
    if not match or not match["name"]:
        return option.strip(), ""
    return match["name"].strip(), match["requirements"].strip()


def forwards(apps, schema_editor):
    JoinFormQuestion = apps.get_model("community", "JoinFormQuestion")
    JoinRequest = apps.get_model("community", "JoinRequest")
    Club = apps.get_model("community", "Club")

    question = JoinFormQuestion.objects.filter(id=CLUBS_QUESTION_ID).first()
    if question is None:
        return

    club_by_option = {}
    for option in question.options or []:
        name, requirements = _parse_option(option)
        club, _ = Club.objects.get_or_create(name=name, defaults={"requirements": requirements})
        club_by_option[option] = club

    for join_request in JoinRequest.objects.all():
        answer = (join_request.custom_answers or {}).get(CLUBS_QUESTION_ID, {}).get("answer")
        if isinstance(answer, list):
            join_request.interested_clubs.set(
                [club_by_option[a] for a in answer if a in club_by_option]
            )

    question.delete()


class Migration(migrations.Migration):
    dependencies = [("community", "0159_joinrequest_interested_clubs")]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
