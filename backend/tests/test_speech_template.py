import pytest
from community.models import SpeechTemplate

URL = "/api/community/speech-template/"


@pytest.fixture(autouse=True)
def empty_template(db):
    SpeechTemplate.objects.all().delete()


@pytest.mark.django_db
class TestGetSpeechTemplate:
    def test_member_gets_defaults(self, api_client, auth_headers):
        response = api_client.get(URL, **auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["shared_pm"] == ""
        assert data["walk_pm"] == ""
        assert data["restaurant_pm"] == ""
        assert data["open_roles"] == []
        assert "updated_at" in data

    def test_unauthenticated_denied(self, api_client):
        assert api_client.get(URL).status_code == 401
