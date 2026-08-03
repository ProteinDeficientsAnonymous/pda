"""Contract tests: question field_type enums stay named in OpenAPI."""

import json
from pathlib import Path

import pytest

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "openapi_schema.json"


def _schemas() -> dict:
    return json.loads(SCHEMA_PATH.read_text())["components"]["schemas"]


def _field_type_schema(model_name: str) -> dict:
    return _schemas()[model_name]["properties"]["field_type"]


@pytest.mark.unit
def test_join_form_question_out_uses_named_enum():
    field = _field_type_schema("JoinFormQuestionOut")
    assert field == {"$ref": "#/components/schemas/JoinFormQuestionType"}
    assert _schemas()["JoinFormQuestionType"]["enum"] == ["text", "textarea", "dropdown"]


@pytest.mark.unit
def test_survey_question_schemas_use_named_enum():
    assert _field_type_schema("SurveyQuestionIn") == {
        "allOf": [{"$ref": "#/components/schemas/SurveyQuestionType"}],
        "default": "text",
    }
    assert _field_type_schema("SurveyQuestionOut") == {
        "$ref": "#/components/schemas/SurveyQuestionType"
    }
    assert set(_schemas()["SurveyQuestionType"]["enum"]) == {
        "text",
        "textarea",
        "select",
        "multiselect",
        "dropdown",
        "number",
        "yes_no",
        "rating",
        "datetime_poll",
    }
