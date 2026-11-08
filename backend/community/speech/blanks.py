from typing import NamedTuple

MAX_STRING_LEN = 2000
MAX_LIST_ITEMS = 20
MAX_LIST_ITEM_LEN = 300

SpeechValues = dict[str, str | list[str]]


class BlankDef(NamedTuple):
    label: str
    is_list: bool


BLANKS: dict[str, BlankDef] = {
    "facilitators": BlankDef("facilitators", False),
    "open_roles": BlankDef("open roles", True),
    "upcoming_events": BlankDef("upcoming events", True),
    "intro_question": BlankDef("intro question", False),
    "front_walker": BlankDef("front walker", False),
    "back_walker": BlankDef("back walker", False),
    "walk_details": BlankDef("walk details", False),
    "restaurant": BlankDef("restaurant", False),
}


def _clean_string(key: str, value: object) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    if len(value) > MAX_STRING_LEN:
        raise ValueError(f"{key} must be at most {MAX_STRING_LEN} characters")
    return value


def _clean_list(key: str, value: object) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{key} must be a list")
    if len(value) > MAX_LIST_ITEMS:
        raise ValueError(f"{key} must have at most {MAX_LIST_ITEMS} items")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"{key} items must be strings")
        if len(item) > MAX_LIST_ITEM_LEN:
            raise ValueError(f"{key} items must be at most {MAX_LIST_ITEM_LEN} characters")
        items.append(item)
    return items


def clean_values(raw: dict) -> SpeechValues:
    """Drop unknown keys and validate types/limits; raises ValueError on bad input."""
    cleaned: SpeechValues = {}
    for key, blank in BLANKS.items():
        if key not in raw:
            continue
        cleaned[key] = _clean_list(key, raw[key]) if blank.is_list else _clean_string(key, raw[key])
    return cleaned
