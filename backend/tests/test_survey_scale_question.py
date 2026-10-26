from community._survey_schemas import SurveyQuestionIn
from community.models import SurveyQuestionType


def test_scale_takes_no_options():
    q = SurveyQuestionIn(label="pace", field_type=SurveyQuestionType.SCALE, options=["slow"])
    assert q.options == []
