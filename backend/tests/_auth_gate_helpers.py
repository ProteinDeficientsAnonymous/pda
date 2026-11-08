from django.utils import timezone

BLOCK_CODES = {
    "paused": "auth.account_paused",
    "archived": "auth.account_archived",
    "needs_password_reset": "auth.password_reset_required",
    "needs_onboarding": "auth.onboarding_required",
    "needs_guidelines_consent": "auth.guidelines_consent_required",
}


def block_user(user, block: str) -> None:
    if block == "paused":
        user.is_paused = True
        user.save(update_fields=["is_paused"])
        return
    if block == "archived":
        user.archived_at = timezone.now()
        user.save(update_fields=["archived_at"])
        return
    if block == "needs_onboarding":
        user.needs_onboarding = True
        user.save(update_fields=["needs_onboarding"])
        return
    if block == "needs_guidelines_consent":
        user.guidelines_consent_at = None
        user.save(update_fields=["guidelines_consent_at"])
        return
    user.needs_password_reset = True
    user.save(update_fields=["needs_password_reset"])
