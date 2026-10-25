import json
from datetime import timedelta

import pytest
from audit.models import AuditLogEntry
from community._validation import Code
from community.models import Event, EventType, PageVisibility, Survey, SurveyResponse
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role

from tests._asserts import assert_error_code

JSON = "application/json"
URL = "/api/community/surveys/"


@pytest.fixture
def surveys_admin(db):
    user = User.objects.create_user(
        phone_number="+12025557200", password="x", first_name="Surveys", last_name="Admin"
    )
    role = Role.objects.create(name="surveys_admin", permissions=[PermissionKey.MANAGE_SURVEYS])
    user.roles.add(role)
    return user


@pytest.fixture
def admin_headers(surveys_admin):
    refresh = RefreshToken.for_user(surveys_admin)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


def _post(client, payload, headers):
    return client.post(URL, data=json.dumps(payload), content_type=JSON, **headers)


def _patch(client, survey_id, payload, headers):
    return client.patch(
        f"{URL}{survey_id}/", data=json.dumps(payload), content_type=JSON, **headers
    )


def _payload(slug="fb", **extra):
    return {"title": "Feedback", "slug": slug, **extra}


@pytest.mark.django_db
class TestFeedbackType:
    def test_create_feedback_survey_forces_anonymous(self, api_client, admin_headers):
        resp = _post(
            api_client,
            _payload(feedback_event_type="official", anonymous=False),
            admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["anonymous"] is True
        assert data["feedback_event_type"] == "official"

    def test_feedback_type_taken_returns_400(self, api_client, admin_headers):
        Survey.objects.create(title="Existing", slug="existing", feedback_event_type="club")
        resp = _post(api_client, _payload(feedback_event_type="club"), admin_headers)
        assert resp.status_code == 400
        assert_error_code(resp, Code.Survey.FEEDBACK_TYPE_TAKEN, "feedback_event_type")

    def test_patch_taken_by_other_returns_400(self, api_client, admin_headers):
        Survey.objects.create(title="Existing", slug="existing", feedback_event_type="club")
        other = Survey.objects.create(title="Other", slug="other")
        resp = _patch(api_client, other.id, {"feedback_event_type": "club"}, admin_headers)
        assert resp.status_code == 400
        assert_error_code(resp, Code.Survey.FEEDBACK_TYPE_TAKEN, "feedback_event_type")

    def test_patch_same_survey_keeps_type(self, api_client, admin_headers):
        survey = Survey.objects.create(title="Own", slug="own", feedback_event_type="club")
        resp = _patch(api_client, survey.id, {"title": "Renamed"}, admin_headers)
        assert resp.status_code == 200
        assert resp.json()["feedback_event_type"] == "club"
        survey.refresh_from_db()
        assert survey.anonymous is True

    def test_title_only_patch_on_typed_survey_changes_only_title(
        self, api_client, admin_headers, django_capture_on_commit_callbacks
    ):
        survey = Survey.objects.create(
            title="Own", slug="own", feedback_event_type="club", anonymous=True
        )
        with django_capture_on_commit_callbacks(execute=True):
            resp = _patch(api_client, survey.id, {"title": "Renamed"}, admin_headers)
        assert resp.status_code == 200
        entry = AuditLogEntry.objects.get(action="survey_updated")
        assert entry.details["fields_changed"] == ["title"]

    def test_community_type_rejected(self, api_client, admin_headers):
        resp = _post(api_client, _payload(feedback_event_type="community"), admin_headers)
        assert resp.status_code == 422
        survey = Survey.objects.create(title="Plain", slug="plain")
        resp = _patch(api_client, survey.id, {"feedback_event_type": "community"}, admin_headers)
        assert resp.status_code == 422

    def test_patch_sets_type_and_forces_anonymous(self, api_client, admin_headers):
        survey = Survey.objects.create(title="Plain", slug="plain")
        resp = _patch(api_client, survey.id, {"feedback_event_type": "official"}, admin_headers)
        assert resp.status_code == 200
        survey.refresh_from_db()
        assert survey.feedback_event_type == "official"
        assert survey.anonymous is True

    def test_patch_clears_feedback_type(self, api_client, admin_headers):
        survey = Survey.objects.create(
            title="Fb", slug="fb2", feedback_event_type="official", anonymous=True
        )
        resp = _patch(api_client, survey.id, {"feedback_event_type": ""}, admin_headers)
        assert resp.status_code == 200
        assert resp.json()["feedback_event_type"] == ""
        survey.refresh_from_db()
        assert survey.feedback_event_type == ""

    def test_feedback_survey_drops_linked_event(self, api_client, admin_headers, surveys_admin):
        event = Event.objects.create(
            title="Potluck",
            start_datetime=timezone.now() + timedelta(days=3),
            event_type=EventType.OFFICIAL,
            visibility=PageVisibility.PUBLIC,
            created_by=surveys_admin,
        )
        resp = _post(
            api_client,
            _payload(feedback_event_type="official", linked_event_id=str(event.id)),
            admin_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["linked_event_id"] is None

    def test_patch_drops_linked_event_when_marking(self, api_client, admin_headers, surveys_admin):
        event = Event.objects.create(
            title="Potluck",
            start_datetime=timezone.now() + timedelta(days=3),
            event_type=EventType.OFFICIAL,
            visibility=PageVisibility.PUBLIC,
            created_by=surveys_admin,
        )
        survey = Survey.objects.create(title="Linked", slug="linked", linked_event=event)
        resp = _patch(api_client, survey.id, {"feedback_event_type": "club"}, admin_headers)
        assert resp.status_code == 200
        survey.refresh_from_db()
        assert survey.linked_event is None

    def test_cannot_force_anonymous_after_named_responses(self, api_client, admin_headers):
        survey = Survey.objects.create(title="Named", slug="named", anonymous=False)
        SurveyResponse.objects.create(survey=survey, answers={})
        resp = _patch(api_client, survey.id, {"feedback_event_type": "official"}, admin_headers)
        assert resp.status_code == 400
        assert_error_code(resp, Code.Survey.ANONYMOUS_LOCKED)
