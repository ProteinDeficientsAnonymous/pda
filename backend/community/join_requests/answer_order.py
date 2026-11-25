"""Order a join request's answers the way the join form asks them."""

from community.join_requests.clubs_question import CLUBS_QUESTION_ID
from community.models import JoinFormQuestion


def question_order() -> dict[str, int]:
    """return(dict): each question id's position on the form; the built-in clubs question is last."""
    ids = JoinFormQuestion.objects.values_list("id", flat=True)
    order = {str(qid): position for position, qid in enumerate(ids)}
    order[CLUBS_QUESTION_ID] = len(order)
    return order


def in_form_order(custom_answers: dict, order: dict[str, int]) -> list[tuple[str, dict]]:
    # Postgres jsonb doesn't keep key order. Answers to deleted questions go last, in stored order.
    return sorted(custom_answers.items(), key=lambda item: order.get(item[0], len(order)))
