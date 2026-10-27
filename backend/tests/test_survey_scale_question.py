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
        ([" never ", "", "sometimes", "", "always"], ["never", "", "sometimes", "", "always"]),
        ([""] * 5, []),
    ],
)
def test_scale_keeps_end_or_point_labels(options, saved):
    assert _scale(options).options == saved


@pytest.mark.parametrize("count", [3, 4, 6])
def test_scale_refuses_labels_that_fit_neither_ends_nor_points(count):
    with pytest.raises(ValidationError, match="2 end labels .* or 5 point labels"):
        _scale(["x"] * count)


def test_stars_take_no_labels():
    q = SurveyQuestionIn(label="vibes", field_type=SurveyQuestionType.STARS, options=["meh"])
    assert q.options == []
