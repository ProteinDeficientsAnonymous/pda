"""Tests for feedback (GitHub issue creation) endpoint."""

import pytest


def _mock_urlopen(monkeypatch, issue_url="https://github.com/leahpeker/pda/issues/1"):
    """Patch community.api.urlopen to return a fake GitHub issue creation response."""
    import io
    import json

    captured: dict = {"calls": []}

    def fake_urlopen(request):
        captured["calls"].append(request)
        buf = io.BytesIO(json.dumps({"html_url": issue_url}).encode())
        buf.status = 201  # ty: ignore[unresolved-attribute]
        return buf

    monkeypatch.setattr("community._feedback.urlopen", fake_urlopen)
    return captured


_APP_SETTINGS = {
    "GITHUB_APP_ID": "12345",
    "GITHUB_APP_INSTALLATION_ID": "67890",
    "GITHUB_APP_PRIVATE_KEY": "fake-key",
    "GITHUB_REPO": "ProteinDeficientsAnonymous/pda",
}


@pytest.mark.django_db
class TestFeedback:
    def test_feedback_success_creates_github_issue(
        self, api_client, auth_headers, settings, monkeypatch
    ):
        for k, v in _APP_SETTINGS.items():
            setattr(settings, k, v)
        monkeypatch.setattr(
            "community._feedback._get_github_app_token", lambda *_: "ghs_inst_token"
        )
        captured = _mock_urlopen(monkeypatch)

        response = api_client.post(
            "/api/community/feedback/",
            {
                "title": "Bug: calendar not loading",
                "description": "The calendar page shows a spinner forever",
                "metadata": {
                    "route": "/calendar",
                    "user_agent": "Mozilla/5.0",
                    "app_version": "1.0.0+1",
                },
            },
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 201
        assert "html_url" in response.json()

        issue_request = captured["calls"][-1]
        assert (
            "api.github.com/repos/ProteinDeficientsAnonymous/pda/issues" in issue_request.full_url
        )
        assert issue_request.get_header("Authorization") == "Bearer ghs_inst_token"

    def test_feedback_works_without_auth(self, api_client, settings, monkeypatch):
        for k, v in _APP_SETTINGS.items():
            setattr(settings, k, v)
        monkeypatch.setattr(
            "community._feedback._get_github_app_token", lambda *_: "ghs_inst_token"
        )
        _mock_urlopen(monkeypatch)

        response = api_client.post(
            "/api/community/feedback/",
            {
                "title": "Bug from anonymous user",
                "description": "Something is wrong",
            },
            content_type="application/json",
        )
        assert response.status_code == 201

    def test_feedback_returns_503_when_app_not_configured(self, api_client, settings):
        settings.GITHUB_APP_ID = ""
        settings.GITHUB_APP_INSTALLATION_ID = ""
        settings.GITHUB_APP_PRIVATE_KEY = ""
        settings.GITHUB_REPO = ""

        response = api_client.post(
            "/api/community/feedback/",
            {
                "title": "Bug report",
                "description": "Details here",
            },
            content_type="application/json",
        )
        assert response.status_code == 503

    def test_feedback_requires_title(self, api_client, settings):
        for k, v in _APP_SETTINGS.items():
            setattr(settings, k, v)

        response = api_client.post(
            "/api/community/feedback/",
            {"description": "Missing title"},
            content_type="application/json",
        )
        assert response.status_code == 422

    def test_feedback_rejects_empty_title(self, api_client, settings):
        for k, v in _APP_SETTINGS.items():
            setattr(settings, k, v)

        response = api_client.post(
            "/api/community/feedback/",
            {"title": "", "description": "Some description"},
            content_type="application/json",
        )
        assert response.status_code == 422

    def test_feedback_requires_description(self, api_client, settings):
        for k, v in _APP_SETTINGS.items():
            setattr(settings, k, v)

        response = api_client.post(
            "/api/community/feedback/",
            {"title": "Bug report"},
            content_type="application/json",
        )
        assert response.status_code == 422

    def test_feedback_rejects_empty_description(self, api_client, settings):
        for k, v in _APP_SETTINGS.items():
            setattr(settings, k, v)

        response = api_client.post(
            "/api/community/feedback/",
            {"title": "Bug report", "description": ""},
            content_type="application/json",
        )
        assert response.status_code == 422

    def test_feedback_issue_body_uses_user_id_and_omits_name_and_phone(
        self, api_client, settings, monkeypatch
    ):
        """Submitter identity in issue body should be the user's UUID, not name or phone."""
        import json

        for k, v in _APP_SETTINGS.items():
            setattr(settings, k, v)
        monkeypatch.setattr(
            "community._feedback._get_github_app_token", lambda *_: "ghs_inst_token"
        )
        captured = _mock_urlopen(monkeypatch)

        from users.models import User

        user = User.objects.create_user(
            phone_number="+15551239999",
            password="pw12345678",
            display_name="alice smith",
        )
        from ninja_jwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(user)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore

        response = api_client.post(
            "/api/community/feedback/",
            {
                "title": "something broke",
                "description": "details",
                "metadata": {},
            },
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 201

        issue_request = captured["calls"][-1]
        body_payload = json.loads(issue_request.data.decode())
        issue_body = body_payload["body"]
        assert str(user.id) in issue_body
        assert "alice" not in issue_body
        assert "smith" not in issue_body
        assert "+15551239999" not in issue_body
        assert "Phone" not in issue_body
        assert "User:" not in issue_body

    def test_feedback_schema_ignores_removed_fields(self, api_client, settings, monkeypatch):
        """user_phone and user_display_name were removed — extra fields should be ignored, not break."""
        for k, v in _APP_SETTINGS.items():
            setattr(settings, k, v)
        monkeypatch.setattr(
            "community._feedback._get_github_app_token", lambda *_: "ghs_inst_token"
        )
        _mock_urlopen(monkeypatch)

        response = api_client.post(
            "/api/community/feedback/",
            {
                "title": "t",
                "description": "d",
                "metadata": {
                    "user_phone": "+15551234567",
                    "user_display_name": "alice smith",
                },
            },
            content_type="application/json",
        )
        assert response.status_code == 201

    def test_feedback_returns_503_on_github_api_failure(self, api_client, settings, monkeypatch):
        from urllib.error import URLError

        for k, v in _APP_SETTINGS.items():
            setattr(settings, k, v)
        monkeypatch.setattr(
            "community._feedback._get_github_app_token", lambda *_: "ghs_inst_token"
        )
        monkeypatch.setattr(
            "community._feedback.urlopen",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(URLError("Connection refused")),
        )

        response = api_client.post(
            "/api/community/feedback/",
            {
                "title": "Bug report",
                "description": "Details here",
            },
            content_type="application/json",
        )
        assert response.status_code == 503
        assert response.json()["detail"][0]["code"] == "feedback.creation_failed"
