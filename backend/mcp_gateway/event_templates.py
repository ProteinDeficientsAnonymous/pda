import re

# Official templates mark slots as [ALL CAPS ...]; any lowercase letter means it isn't a slot.
SLOT_RE = re.compile(r"\[([A-Z][^\[\]a-z]*)\]")


def template_slots(text: str) -> list[str]:
    return list(dict.fromkeys(SLOT_RE.findall(text)))
