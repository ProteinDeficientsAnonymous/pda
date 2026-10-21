from community.models import ShowIfOperator, SurveyQuestion


def make_question(survey, label, field_type, order=0, **fields):
    return SurveyQuestion.objects.create(
        survey=survey,
        label=label,
        field_type=field_type,
        display_order=order,
        **fields,
    )


def equals(question, value):
    return {
        "question_id": str(question.id),
        "operator": ShowIfOperator.EQUALS.value,
        "value": value,
    }


def not_equals(question, value):
    return {
        "question_id": str(question.id),
        "operator": ShowIfOperator.NOT_EQUALS.value,
        "value": value,
    }
