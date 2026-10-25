import pytest


@pytest.mark.django_db
class TestHostDigestPrefs:
    def test_patch_me_sets_host_digest_opt_out(self, api_client, auth_headers, test_user):
        response = api_client.patch(
            "/api/auth/me/",
            {"host_digest_opt_out": True},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["host_digest_opt_out"] is True
        test_user.refresh_from_db()
        assert test_user.host_digest_opt_out is True

    def test_me_defaults_to_opted_in(self, api_client, auth_headers):
        response = api_client.get("/api/auth/me/", **auth_headers)
        assert response.status_code == 200
        assert response.json()["host_digest_opt_out"] is False

    def test_me_does_not_expose_last_sent_at(self, api_client, auth_headers):
        response = api_client.get("/api/auth/me/", **auth_headers)
        assert response.status_code == 200
        assert "host_digest_last_sent_at" not in response.json()
