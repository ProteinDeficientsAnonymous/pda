import pytest
from community.models import Event, EventFormat
from users.permissions import PermissionKey

from tests._auth import auth_headers_for
from tests._users import make_user


@pytest.fixture
def dev_tools_headers(db):
    return auth_headers_for(make_user(PermissionKey.MANAGE_EVENTS))


@pytest.mark.django_db
class TestDevTestEventFormat:
    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            ({"is_official": True}, EventFormat.WALK),
            ({"is_official": True, "event_format": "restaurant"}, EventFormat.RESTAURANT),
            ({}, ""),
            ({"is_club": True}, ""),
        ],
    )
    def test_event_format_set_only_on_official(
        self, api_client, dev_tools_headers, monkeypatch, data, expected
    ):
        monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
        response = api_client.post(
            "/api/community/dev/test-events/",
            data=data,
            content_type="application/json",
            **dev_tools_headers,
        )
        assert response.status_code == 201
        assert Event.objects.get(id=response.json()["id"]).event_format == expected

    @pytest.mark.parametrize(
        "data",
        [
            {"is_official": True, "event_format": "picnic"},
            {"event_format": "picnic"},
            {"event_format": "restaurant"},
            {"is_club": True, "event_format": "walk"},
        ],
    )
    def test_invalid_event_format_rejected(self, api_client, dev_tools_headers, monkeypatch, data):
        monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
        response = api_client.post(
            "/api/community/dev/test-events/",
            data=data,
            content_type="application/json",
            **dev_tools_headers,
        )
        assert response.status_code == 422
        assert not Event.objects.exists()
