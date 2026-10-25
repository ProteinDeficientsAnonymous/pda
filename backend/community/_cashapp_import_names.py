import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field

from community._cashapp_import_types import GuestRecord

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalize_name(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    ascii_ish = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(_NON_ALNUM.sub(" ", ascii_ish.lower()).split())


def _keys(*parts: str) -> set[str]:
    return {normalize_name(p) for p in parts} - {""}


def full_name_keys(guest: GuestRecord) -> set[str]:
    """Multi-word forms only: full name, nickname + last, first + nickname."""
    candidates = _keys(
        f"{guest.first_name} {guest.last_name}",
        f"{guest.nickname} {guest.last_name}" if guest.nickname else "",
        f"{guest.first_name} {guest.nickname}" if guest.nickname else "",
    )
    return {k for k in candidates if " " in k}


def single_name_keys(guest: GuestRecord) -> set[str]:
    return {k for k in _keys(guest.first_name, guest.nickname) if " " not in k and len(k) > 1}


@dataclass
class NameIndex:
    """Sender lookups use full forms plus a bare nickname, mirroring the partiful import."""

    sender: dict[str, list[GuestRecord]] = field(default_factory=lambda: defaultdict(list))
    sender_nickname: dict[str, list[GuestRecord]] = field(default_factory=lambda: defaultdict(list))
    note_full: dict[str, list[GuestRecord]] = field(default_factory=lambda: defaultdict(list))
    note_single: dict[str, list[GuestRecord]] = field(default_factory=lambda: defaultdict(list))
    max_tokens: int = 1

    @classmethod
    def build(cls, guests: list[GuestRecord]) -> "NameIndex":
        index = cls()
        for guest in guests:
            full = full_name_keys(guest)
            for key in full:
                index.sender[key].append(guest)
            for key in _keys(guest.nickname) - full:
                index.sender_nickname[key].append(guest)
            for key in full:
                index.note_full[key].append(guest)
                index.max_tokens = max(index.max_tokens, key.count(" ") + 1)
            for key in single_name_keys(guest):
                index.note_single[key].append(guest)
        return index

    def sender_matches(self, sender_name: str) -> tuple[list[GuestRecord], bool]:
        """return(tuple): (matching guests, True when only a bare nickname matched)."""
        key = normalize_name(sender_name)
        full = self.sender.get(key, [])
        nickname = self.sender_nickname.get(key, [])
        if full:
            return list({g.user_id: g for g in full + nickname}.values()), False
        return list(nickname), bool(nickname)

    def note_hits(
        self, note: str
    ) -> tuple[dict[str, list[GuestRecord]], dict[str, list[GuestRecord]]]:
        """return(tuple): (full-name hits, single-name hits), each keyed by the matched text."""
        tokens = normalize_name(note).split()
        grams = {
            " ".join(tokens[i : i + n])
            for n in range(1, self.max_tokens + 1)
            for i in range(len(tokens) - n + 1)
        }
        full = {g: self.note_full[g] for g in grams if g in self.note_full}
        single = {g: self.note_single[g] for g in grams if g in self.note_single}
        return full, single
