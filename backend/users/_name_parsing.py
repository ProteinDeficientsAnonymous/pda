def parse_display_name(display_name: str) -> tuple[str, str]:
    """Split a legacy display_name into (first_name, last_name).

    Last whitespace-delimited word becomes the last name; everything before it
    is the first name. A single word is the first name with a blank last name.
    """
    words = (display_name or "").split()
    if not words:
        return "", ""
    if len(words) == 1:
        return words[0], ""
    return " ".join(words[:-1]), words[-1]


def sync_display_name(instance, kwargs: dict, max_length: int = 64) -> None:
    """Sync the transitional display_name column from full_name (truncated).

    Shared by User.save() and JoinRequest.save(). A blank full_name leaves the
    existing display_name untouched (a genuinely nameless record has no display
    name to sync from — clearing it here would erase history on unrelated saves).
    Truncates to max_length since full_name (up to 129 chars for two 64-char
    fields) can exceed the display_name column width. Mutates kwargs in place so
    a restricted update_fields still writes the synced column.
    """
    if instance.full_name:
        instance.display_name = instance.full_name[:max_length]
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            update_fields = set(update_fields)
            update_fields.add("display_name")
            kwargs["update_fields"] = update_fields
