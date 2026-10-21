"""Optional-JWT public writes: hard-blocked tokens 403, pending tokens act anonymously."""

import json

import pytest
from community.models import Survey, SurveyQuestion, SurveyQuestionType, SurveyResponse
from users.models import User

from tests.test_auth_gate import _BLOCK_CODES, _block_user, _headers

_FEEDBACK_BODY = {
    "title": "Bug from a gated account",
    "description": "the guidelines page",
    "metadata": {"route": "/guidelines", "user_agent": "test", "app_version": "0"},
}

_FEEDBACK_SETTINGS = {
    "GITHUB_APP_ID": "12345",
    "GITHUB_APP_INSTALLATION_ID": "67890",
    "GITHUB_APP_PRIVATE_KEY": "fake-key",
    "GITHUB_REPO": "ProteinDeficientsAnonymous/pda",
}


def _mock_feedback_github(monkeypatch, settings):
    for key, value in _FEEDBACK_SETTINGS.items():
        setattr(settings, key, value)
    monkeypatch.setattr("community._feedback._get_github_app_token", lambda *_: "ghs_inst_token")
    captured: list = []

    def fake_urlopen(request):
        captured.append(request.data)
        return _FakeGitHubResponse()

    monkeypatch.setattr("community._feedback.urlopen", fake_urlopen)
    return captured


class _FakeGitHubResponse:
    status = 201

    def read(self):
        return b'{"html_url": "https://github.com/example/pda/issues/1"}'

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


@pytest.mark.django_db
class TestOptionalJwtAnonymousWrites:
    @pytest.mark.parametrize("block", ["paused", "archived"])
    def test_hard_block_cannot_submit_feedback(self, api_client, block):
        user = User.objects.create_user(
            phone_number="+12025550340" if block == "paused" else "+12025550341",
            password="pass",
            first_name="Hard",
            last_name="Feedback",
        )
        headers = _headers(user)
        _block_user(user, block)

        resp = api_client.post(
            "/api/community/feedback/",
            _FEEDBACK_BODY,
            content_type="application/json",
            **headers,
        )
        assert resp.status_code == 403
        assert resp.json()["detail"][0]["code"] == _BLOCK_CODES[block]

    @pytest.mark.parametrize(
        "block", ["needs_onboarding", "needs_guidelines_consent", "needs_password_reset"]
    )
    def test_pending_token_submits_feedback_as_anonymous(
        self, api_client, settings, monkeypatch, block
    ):
        phones = {
            "needs_onboarding": "+12025550342",
            "needs_guidelines_consent": "+12025550343",
            "needs_password_reset": "+12025550344",
        }
        user = User.objects.create_user(
            phone_number=phones[block],
            password="pass",
            first_name="Pending",
            last_name="Feedback",
        )
        headers = _headers(user)
        _block_user(user, block)
        captured = _mock_feedback_github(monkeypatch, settings)

        resp = api_client.post(
            "/api/community/feedback/",
            _FEEDBACK_BODY,
            content_type="application/json",
            **headers,
        )
        assert resp.status_code == 201, resp.content
        issue = json.loads(captured[-1])
        assert str(user.id) not in issue["body"]

    @pytest.mark.parametrize("block", ["paused", "archived"])
    def test_hard_block_cannot_respond_to_public_survey(self, api_client, block):
        survey = Survey.objects.create(title="Gate", slug=f"gate-hard-{block}")
        question = SurveyQuestion.objects.create(
            survey=survey, label="Mood", field_type=SurveyQuestionType.TEXT
        )
        user = User.objects.create_user(
            phone_number="+12025550345" if block == "paused" else "+12025550346",
            password="pass",
            first_name="Hard",
            last_name="Survey",
        )
        headers = _headers(user)
        _block_user(user, block)

        resp = api_client.post(
            f"/api/community/surveys/view/{survey.slug}/respond/",
            {"answers": {str(question.id): "nope"}},
            content_type="application/json",
            **headers,
        )
        assert resp.status_code == 403
        assert resp.json()["detail"][0]["code"] == _BLOCK_CODES[block]
        assert not SurveyResponse.objects.filter(survey=survey).exists()

    @pytest.mark.parametrize(
        "block", ["needs_onboarding", "needs_guidelines_consent", "needs_password_reset"]
    )
    def test_pending_token_responds_to_public_survey_as_anonymous(self, api_client, block):
        survey = Survey.objects.create(title="Gate", slug=f"gate-pending-{block}")
        question = SurveyQuestion.objects.create(
            survey=survey, label="Mood", field_type=SurveyQuestionType.TEXT
        )
        phones = {
            "needs_onboarding": "+12025550347",
            "needs_guidelines_consent": "+12025550348",
            "needs_password_reset": "+12025550349",
        }
        user = User.objects.create_user(
            phone_number=phones[block],
            password="pass",
            first_name="Pending",
            last_name="Survey",
        )
        headers = _headers(user)
        _block_user(user, block)

        resp = api_client.post(
            f"/api/community/surveys/view/{survey.slug}/respond/",
            {"answers": {str(question.id): "hello"}},
            content_type="application/json",
            **headers,
        )
        assert resp.status_code == 201, resp.content
        saved = SurveyResponse.objects.get(survey=survey)
        assert saved.user_id is None
