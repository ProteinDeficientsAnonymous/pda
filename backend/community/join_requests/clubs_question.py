"""The built-in "which clubs are you interested in?" join-form question, built from the Club list."""

from community.models import Club, JoinFormQuestion, JoinFormQuestionType

# Reuses the id of the old admin-created question so already-submitted answers stay keyed.
CLUBS_QUESTION_ID = "266d97e3-56c9-4edc-805e-85a234cc58f9"


def club_option(club: Club) -> str:
    return f"{club.name} ({club.requirements})" if club.requirements else club.name


def build_clubs_question() -> tuple[JoinFormQuestion, list[Club]] | None:
    """Unsaved question plus its clubs (option order); None when there are no clubs."""
    clubs = list(Club.objects.all())
    if not clubs:
        return None
    question = JoinFormQuestion(
        id=CLUBS_QUESTION_ID,
        label="which clubs are you interested in?",
        field_type=JoinFormQuestionType.CHECKBOX,
        options=[club_option(c) for c in clubs],
        required=False,
    )
    return question, clubs


def clubs_for_answer(clubs: list[Club], answer: list[str] | str) -> list[Club]:
    chosen = set(answer) if isinstance(answer, list) else set()
    return [c for c in clubs if club_option(c) in chosen]
