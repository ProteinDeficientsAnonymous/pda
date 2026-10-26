import pytest
from community._survey_schemas import SurveyQuestionIn
from community.models import SurveyQuestionType
from pydantic import ValidationError


def _scale(options: list[str]) -> SurveyQuestionIn:
    return SurveyQuestionIn(label="pace", field_type=SurveyQuestionType.SCALE, options=options)


@pytest.mark.parametrize(
    ("options", "saved"),
    [
        ([" slow ", "fast"], ["slow", "fast"]),
        (["slow"], ["slow", ""]),
        (["", "fast"], ["", "fast"]),
        ([" ", ""], []),
        ([], []),
    ],
)
def test_scale_keeps_low_and_high_end_labels(options, saved):
    assert _scale(options).options == saved


def test_scale_refuses_more_than_two_end_labels():
    with pytest.raises(ValidationError, match="at most 2 end labels"):
        _scale(["slow", "ok", "fast"])


def test_stars_take_no_labels():
    q = SurveyQuestionIn(label="vibes", field_type=SurveyQuestionType.STARS, options=["meh"])
    assert q.options == []
