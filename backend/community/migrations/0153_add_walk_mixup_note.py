import json

from django.db import migrations

NOTE_TEXT = (
    "don't forget to stay together. mix it up halfway through the walk, and again after "
    "the walk ends: about 15 min into eating, or when people seem done eating"
)
NOTE = {
    "type": "blockquote",
    "content": [{"type": "paragraph", "content": [{"type": "text", "text": NOTE_TEXT}]}],
}


def _nodes(node: dict):
    yield node
    for child in node.get("content") or []:
        if isinstance(child, dict):
            yield from _nodes(child)


def _text(node: dict) -> str:
    return "".join(n.get("text", "") for n in _nodes(node) if n.get("type") == "text")


def _has_mixup_note(doc: dict) -> bool:
    return any("halfway" in _text(n).lower() for n in _nodes(doc) if n.get("type") == "blockquote")


def add_walk_mixup_note(template_model) -> None:
    template = template_model.objects.filter(pk=1).first()
    if template is None:
        return
    try:
        doc = json.loads(template.walk_pm)
    except ValueError:
        return
    if not isinstance(doc, dict) or doc.get("type") != "doc":
        return
    if not isinstance(doc.get("content"), list):
        return
    if not _text(doc).strip() or _has_mixup_note(doc):
        return
    doc["content"].append(NOTE)
    template.walk_pm = json.dumps(doc)
    template.save(update_fields=["walk_pm", "updated_at"])


def _add_note(apps, _schema_editor):
    add_walk_mixup_note(apps.get_model("community", "SpeechTemplate"))


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0152_perf_indexes"),
    ]

    operations = [
        migrations.RunPython(_add_note, migrations.RunPython.noop),
    ]
