import re
import unicodedata

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalize_name(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    ascii_ish = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(_NON_ALNUM.sub(" ", ascii_ish.lower()).split())
