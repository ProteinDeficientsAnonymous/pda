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
