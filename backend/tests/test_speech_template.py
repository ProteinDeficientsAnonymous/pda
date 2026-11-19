import json

import pytest
from community.models import SpeechTemplate
from users.permissions import PermissionKey

from tests._asserts import assert_error_code
from tests._auth import auth_headers_for
from tests._users import make_user

URL = "/api/community/speech-template/"


def _pm(text: str) -> str:
    return json.dumps(
        {
            "type": "doc",
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}],
        }
    )


@pytest.fixture(autouse=True)
def empty_template(db):
    SpeechTemplate.objects.all().delete()


@pytest.fixture
def editor_headers(db):
    return auth_headers_for(make_user(PermissionKey.EDIT_SPEECH_TEMPLATE, last_name="Editor"))


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


@pytest.mark.django_db
class TestUpdateSpeechTemplate:
    def test_without_permission_is_403(self, api_client, auth_headers):
        response = api_client.patch(
            URL, {"walk_pm": _pm("hi")}, content_type="application/json", **auth_headers
        )
        assert response.status_code == 403
        assert SpeechTemplate.get().walk_pm == ""

    def test_updates_given_fields_only(self, api_client, editor_headers):
        SpeechTemplate.objects.update_or_create(pk=1, defaults={"shared_pm": _pm("keep")})
        walk = _pm("walk")
        response = api_client.patch(
            URL,
            {"walk_pm": walk, "open_roles": ["mods", "photographer"]},
            content_type="application/json",
            **editor_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["walk_pm"] == walk
        assert data["open_roles"] == ["mods", "photographer"]
        assert data["shared_pm"] == _pm("keep")
        t = SpeechTemplate.get()
        assert t.walk_pm == walk
        assert t.shared_pm == _pm("keep")
        assert t.restaurant_pm == ""

    def test_empty_pm_clears_field(self, api_client, editor_headers):
        SpeechTemplate.objects.update_or_create(pk=1, defaults={"walk_pm": _pm("x")})
        response = api_client.patch(
            URL, {"walk_pm": ""}, content_type="application/json", **editor_headers
        )
        assert response.status_code == 200
        assert response.json()["walk_pm"] == ""

    def test_too_many_roles_is_422(self, api_client, editor_headers):
        roles = [f"role {i}" for i in range(21)]
        response = api_client.patch(
            URL, {"open_roles": roles}, content_type="application/json", **editor_headers
        )
        assert response.status_code == 422
        assert_error_code(response, "speech_template.too_many_roles")

    def test_role_too_long_is_422(self, api_client, editor_headers):
        response = api_client.patch(
            URL, {"open_roles": ["x" * 201]}, content_type="application/json", **editor_headers
        )
        assert response.status_code == 422
        assert_error_code(response, "speech_template.role_too_long")

    @pytest.mark.parametrize("bad", ["not json", json.dumps({"type": "paragraph"}), "[]"])
    def test_invalid_pm_is_422(self, api_client, editor_headers, bad):
        response = api_client.patch(
            URL, {"walk_pm": bad}, content_type="application/json", **editor_headers
        )
        assert response.status_code == 422
        assert_error_code(response, "speech_template.invalid_doc")
        assert SpeechTemplate.get().walk_pm == ""

    def test_roles_stripped_and_empties_dropped(self, api_client, editor_headers):
        response = api_client.patch(
            URL, {"open_roles": ["  mods  ", ""]}, content_type="application/json", **editor_headers
        )
        assert response.status_code == 200
        assert response.json()["open_roles"] == ["mods"]
