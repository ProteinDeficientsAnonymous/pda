def is_seed_allowed(env_name: str | None, force: bool) -> bool:
    """Allow local/unset and staging; refuse any other env unless forced."""
    if not env_name or env_name == "staging":
        return True
    return force
