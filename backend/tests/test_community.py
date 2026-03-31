"""Tests for community endpoints: home, guidelines, join requests, check-phone, error report, pages."""

import pytest
from community.models import JoinRequest, JoinRequestStatus
from users.permissions import PermissionKey
from users.roles import Role

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def manage_guidelines_user(db):
    from users.models import User

    user = User.objects.create_user(
        phone_number="+12025550401",
        password="guidelinespass",
        display_name="Guidelines Manager",
    )
    role = Role.objects.create(
        name="content_manager",
        permissions=[PermissionKey.EDIT_GUIDELINES],
    )
    user.roles.add(role)
    return user


@pytest.fixture
def manage_guidelines_headers(manage_guidelines_user):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(manage_guidelines_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def edit_homepage_user(db):
    from users.models import User

    user = User.objects.create_user(
        phone_number="+12025550402",
        password="homepagepass",
        display_name="Homepage Editor",
    )
    role = Role.objects.create(
        name="homepage_editor",
        permissions=[PermissionKey.EDIT_HOMEPAGE],
    )
    user.roles.add(role)
    return user


@pytest.fixture
def edit_homepage_headers(edit_homepage_user):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(edit_homepage_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def edit_faq_user(db):
    from users.models import User

    user = User.objects.create_user(
        phone_number="+12025550403",
        password="faqpass",
        display_name="FAQ Editor",
    )
    role = Role.objects.create(
        name="faq_editor",
        permissions=[PermissionKey.EDIT_FAQ],
    )
    user.roles.add(role)
    return user


@pytest.fixture
def edit_faq_headers(edit_faq_user):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(edit_faq_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def approve_requests_user(db):
    from users.models import User

    user = User.objects.create_user(
        phone_number="+12025550501",
        password="approverpass",
        display_name="Approver",
    )
    role = Role.objects.create(
        name="vetting_team",
        permissions=[PermissionKey.APPROVE_JOIN_REQUESTS],
    )
    user.roles.add(role)
    return user


@pytest.fixture
def approve_requests_headers(approve_requests_user):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(approve_requests_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def pending_join_request(db):
    from community.models import JoinFormQuestion

    q = JoinFormQuestion.objects.filter(required=True).first()
    answers = {}
    if q:
        answers[str(q.id)] = {"label": q.label, "answer": "I love veganism"}
    return JoinRequest.objects.create(
        display_name="Alice Smith",
        phone_number="+12025550601",
        custom_answers=answers,
        status=JoinRequestStatus.PENDING,
    )


# ---------------------------------------------------------------------------
# TestHomePage
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestHomePage:
    def test_get_home_unauthenticated(self, api_client):
        response = api_client.get("/api/community/home/")
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert "join_content" in data
        assert "updated_at" in data

    def test_get_home_authenticated(self, api_client, auth_headers):
        response = api_client.get("/api/community/home/", **auth_headers)
        assert response.status_code == 200

    def test_update_home_content(self, api_client, edit_homepage_headers):
        response = api_client.patch(
            "/api/community/home/",
            {"content": "New main content"},
            content_type="application/json",
            **edit_homepage_headers,
        )
        assert response.status_code == 200
        assert response.json()["content"] == "New main content"

    def test_update_home_join_content(self, api_client, edit_homepage_headers):
        response = api_client.patch(
            "/api/community/home/",
            {"join_content": "New join section"},
            content_type="application/json",
            **edit_homepage_headers,
        )
        assert response.status_code == 200
        assert response.json()["join_content"] == "New join section"

    def test_update_home_both_fields(self, api_client, edit_homepage_headers):
        response = api_client.patch(
            "/api/community/home/",
            {"content": "Main content", "join_content": "Join content"},
            content_type="application/json",
            **edit_homepage_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Main content"
        assert data["join_content"] == "Join content"

    def test_update_home_requires_permission(self, api_client, auth_headers):
        response = api_client.patch(
            "/api/community/home/",
            {"content": "Blocked"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 403

    def test_update_home_requires_auth(self, api_client):
        response = api_client.patch(
            "/api/community/home/",
            {"content": "No auth"},
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_update_home_partial_does_not_overwrite_other_field(
        self, api_client, edit_homepage_headers
    ):
        api_client.patch(
            "/api/community/home/",
            {"content": "First content", "join_content": "First join"},
            content_type="application/json",
            **edit_homepage_headers,
        )
        api_client.patch(
            "/api/community/home/",
            {"content": "Updated content"},
            content_type="application/json",
            **edit_homepage_headers,
        )
        response = api_client.get("/api/community/home/")
        assert response.json()["join_content"] == "First join"
        assert response.json()["content"] == "Updated content"


# ---------------------------------------------------------------------------
# TestGuidelines
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGuidelines:
    def test_get_guidelines_requires_auth(self, api_client):
        response = api_client.get("/api/community/guidelines/")
        assert response.status_code == 401

    def test_update_guidelines_empty_content(self, api_client, manage_guidelines_headers):
        response = api_client.patch(
            "/api/community/guidelines/",
            {"content": ""},
            content_type="application/json",
            **manage_guidelines_headers,
        )
        assert response.status_code == 200
        assert response.json()["content"] == ""

    def test_guidelines_has_updated_at(self, api_client, manage_guidelines_headers, auth_headers):
        api_client.patch(
            "/api/community/guidelines/",
            {"content": "Some content"},
            content_type="application/json",
            **manage_guidelines_headers,
        )
        response = api_client.get("/api/community/guidelines/", **auth_headers)
        assert "updated_at" in response.json()


# ---------------------------------------------------------------------------
# TestJoinRequests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestJoinRequests:
    @pytest.fixture
    def why_join_id(self, db):
        from community.models import JoinFormQuestion

        q = JoinFormQuestion.objects.filter(required=True).first()
        return str(q.id) if q else ""

    def test_submit_empty_display_name(self, api_client, why_join_id):
        response = api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "   ",
                "phone_number": "+12025550701",
                "answers": {why_join_id: "I care"},
            },
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_submit_missing_required_answer(self, api_client):
        response = api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "Alice",
                "phone_number": "+12025550702",
                "answers": {},
            },
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_submit_display_name_too_long(self, api_client, why_join_id):
        response = api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "A" * 65,
                "phone_number": "+12025550703",
                "answers": {why_join_id: "I care"},
            },
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_submit_display_name_with_numbers(self, api_client, why_join_id):
        response = api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "Alice2",
                "phone_number": "+12025550704",
                "answers": {why_join_id: "I care"},
            },
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_approve_already_approved_request(
        self, api_client, approve_requests_headers, pending_join_request
    ):
        api_client.patch(
            f"/api/community/join-requests/{pending_join_request.id}/",
            {"status": "approved"},
            content_type="application/json",
            **approve_requests_headers,
        )
        response = api_client.patch(
            f"/api/community/join-requests/{pending_join_request.id}/",
            {"status": "approved"},
            content_type="application/json",
            **approve_requests_headers,
        )
        assert response.status_code == 400
        assert "already been approved" in response.json()["detail"]

    def test_approve_creates_user_with_member_role(
        self, api_client, approve_requests_headers, pending_join_request, db
    ):
        from users.models import User

        response = api_client.patch(
            f"/api/community/join-requests/{pending_join_request.id}/",
            {"status": "approved"},
            content_type="application/json",
            **approve_requests_headers,
        )
        assert response.status_code == 200
        assert response.json()["temporary_password"] is not None
        user = User.objects.get(phone_number=pending_join_request.phone_number)
        assert user.needs_onboarding is True

    def test_approve_duplicate_phone_skips_user_creation(
        self, api_client, approve_requests_headers, pending_join_request, test_user, db
    ):
        # Make join request phone match an existing user
        pending_join_request.phone_number = test_user.phone_number
        pending_join_request.save()
        response = api_client.patch(
            f"/api/community/join-requests/{pending_join_request.id}/",
            {"status": "approved"},
            content_type="application/json",
            **approve_requests_headers,
        )
        assert response.status_code == 200
        # No temp password since no user was created
        assert response.json()["temporary_password"] is None


# ---------------------------------------------------------------------------
# TestCheckPhone
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCheckPhone:
    def test_check_phone_exists(self, api_client, test_user):
        response = api_client.post(
            "/api/community/check-phone/",
            {"phone_number": test_user.phone_number},
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json()["exists"] is True

    def test_check_phone_not_exists(self, api_client, db):
        response = api_client.post(
            "/api/community/check-phone/",
            {"phone_number": "+12025559999"},
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json()["exists"] is False

    def test_check_phone_invalid_format_returns_false(self, api_client, db):
        response = api_client.post(
            "/api/community/check-phone/",
            {"phone_number": "not-a-phone"},
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json()["exists"] is False


# ---------------------------------------------------------------------------
# TestErrorReport
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestErrorReport:
    def test_error_report_success(self, api_client, auth_headers):
        response = api_client.post(
            "/api/community/error-report/",
            {
                "error": "Something broke",
                "stack_trace": "at line 42",
                "context": "home screen",
            },
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["detail"] == "Error report received."

    def test_error_report_requires_auth(self, api_client):
        response = api_client.post(
            "/api/community/error-report/",
            {"error": "Something broke"},
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_error_report_minimal_fields(self, api_client, auth_headers):
        response = api_client.post(
            "/api/community/error-report/",
            {"error": "Minimal error"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 201

    def test_error_report_error_too_long(self, api_client, auth_headers):
        response = api_client.post(
            "/api/community/error-report/",
            {"error": "x" * 2001},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 422

    def test_error_report_stack_trace_too_long(self, api_client, auth_headers):
        response = api_client.post(
            "/api/community/error-report/",
            {"error": "err", "stack_trace": "x" * 10001},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# TestFeedback
# ---------------------------------------------------------------------------


def _mock_urlopen(monkeypatch, issue_url="https://github.com/leahpeker/pda/issues/1"):
    """Patch community.api.urlopen to return a fake GitHub issue creation response."""
    import io
    import json

    captured: dict = {"calls": []}

    def fake_urlopen(request):
        captured["calls"].append(request)
        buf = io.BytesIO(json.dumps({"html_url": issue_url}).encode())
        buf.status = 201
        return buf

    monkeypatch.setattr("community.api.urlopen", fake_urlopen)
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
        monkeypatch.setattr("community.api._get_github_app_token", lambda *_: "ghs_inst_token")
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
        monkeypatch.setattr("community.api._get_github_app_token", lambda *_: "ghs_inst_token")
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

    def test_feedback_returns_503_on_github_api_failure(self, api_client, settings, monkeypatch):
        from urllib.error import URLError

        for k, v in _APP_SETTINGS.items():
            setattr(settings, k, v)
        monkeypatch.setattr("community.api._get_github_app_token", lambda *_: "ghs_inst_token")
        monkeypatch.setattr(
            "community.api.urlopen",
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
        assert "Failed to create feedback issue" in response.json()["detail"]


# ---------------------------------------------------------------------------
# TestFAQ
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestFAQ:
    def test_get_faq_authenticated(self, api_client, auth_headers):
        response = api_client.get("/api/community/faq/", **auth_headers)
        assert response.status_code == 200
        assert "content" in response.json()
        assert "updated_at" in response.json()

    def test_get_faq_unauthenticated(self, api_client):
        response = api_client.get("/api/community/faq/")
        assert response.status_code == 401

    def test_update_faq_content(self, api_client, edit_faq_headers):
        response = api_client.patch(
            "/api/community/faq/",
            {"content": "New FAQ content"},
            content_type="application/json",
            **edit_faq_headers,
        )
        assert response.status_code == 200
        assert response.json()["content"] == "New FAQ content"

    def test_update_faq_requires_edit_faq_permission(self, api_client, auth_headers):
        response = api_client.patch(
            "/api/community/faq/",
            {"content": "Should be denied"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 403

    def test_update_faq_requires_auth(self, api_client):
        response = api_client.patch(
            "/api/community/faq/",
            {"content": "No auth"},
            content_type="application/json",
        )
        assert response.status_code == 401
