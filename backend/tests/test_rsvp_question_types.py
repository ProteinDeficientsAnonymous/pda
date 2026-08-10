import pytest
from community.models import RSVP_CHOICE_TYPES, EventRSVP, QuestionType, RsvpQuestionType
from django.core.exceptions import FieldDoesNotExist


@pytest.mark.unit
def test_event_rsvp_uses_questionnaire_responses_field():
    field = EventRSVP._meta.get_field("questionnaire_responses")
    assert field.get_internal_type() == "JSONField"
    with pytest.raises(FieldDoesNotExist):
        EventRSVP._meta.get_field("answers")


@pytest.mark.unit
def test_rsvp_question_type_enum_matches_canonical_subset():
    catalog = {
        question_type.name: (question_type.value, question_type.label)
        for question_type in QuestionType
    }
    rsvp = {
        question_type.name: (question_type.value, question_type.label)
        for question_type in RsvpQuestionType
    }

    assert rsvp == {name: catalog[name] for name in ("TEXTAREA", "SELECT", "CHECKBOX")}
    assert [question_type.value for question_type in RsvpQuestionType] == [
        "textarea",
        "select",
        "checkbox",
    ]
    assert RSVP_CHOICE_TYPES == frozenset(
        {RsvpQuestionType.SELECT, RsvpQuestionType.CHECKBOX},
    )
