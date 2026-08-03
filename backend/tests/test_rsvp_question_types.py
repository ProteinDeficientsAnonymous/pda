"""Unit tests for the RSVP question-type subset of the shared catalog."""

import pytest
from community.models import RSVP_CHOICE_TYPES, RsvpQuestionType, SurveyQuestionType
from community.models.choices import QuestionType, QuestionTypeDefinition


@pytest.mark.unit
def test_rsvp_question_type_enum_matches_canonical_subset():
    canonical = {
        name: definition
        for name, definition in vars(QuestionType).items()
        if isinstance(definition, QuestionTypeDefinition)
    }
    survey = {
        question_type.name: (question_type.value, question_type.label)
        for question_type in SurveyQuestionType
    }
    rsvp = {
        question_type.name: (question_type.value, question_type.label)
        for question_type in RsvpQuestionType
    }

    assert survey == canonical
    assert rsvp == {name: canonical[name] for name in ("TEXTAREA", "DROPDOWN", "MULTISELECT")}
    assert [question_type.value for question_type in RsvpQuestionType] == [
        "textarea",
        "dropdown",
        "multiselect",
    ]
    assert RSVP_CHOICE_TYPES == frozenset(
        {RsvpQuestionType.DROPDOWN, RsvpQuestionType.MULTISELECT},
    )
