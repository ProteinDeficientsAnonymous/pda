import pytest

URL = "/api/community/member-restored-email/"


@pytest.mark.django_db
class TestMemberRestoredEmailEndpoints:
    def test_get_returns_default_body_with_whatsapp_link(self, api_client, auth_headers):
        response = api_client.get(URL, **auth_headers)
        assert response.status_code == 200
        assert "${WHATSAPP_LINK}" in response.json()["body"]

    def test_get_unauthenticated_returns_401(self, api_client):
        assert api_client.get(URL).status_code == 401
