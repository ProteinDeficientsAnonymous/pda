import pytest
from community._official_event_defaults import OFFICIAL_CASHAPP_LINK, OFFICIAL_RSVP_QUESTIONS

URL = "/api/community/official-event-defaults/"


@pytest.mark.django_db
class TestGetOfficialEventDefaults:
    def test_authenticated_user_gets_defaults(self, api_client, auth_headers):
        response = api_client.get(URL, **auth_headers)
        assert response.status_code == 200
        assert response.json() == {
            "cashapp_link": OFFICIAL_CASHAPP_LINK,
            "rsvp_questions": [q.model_dump(mode="json") for q in OFFICIAL_RSVP_QUESTIONS],
        }

    def test_four_required_select_questions(self, api_client, auth_headers):
        questions = api_client.get(URL, **auth_headers).json()["rsvp_questions"]
        assert len(questions) == 4
        assert all(q["required"] and q["field_type"] == "select" for q in questions)

    def test_unauthenticated_returns_401(self, api_client):
        assert api_client.get(URL).status_code == 401
