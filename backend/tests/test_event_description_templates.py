import pytest
from community._event_description_templates import (
    OFFICIAL_NON_WALK_TEMPLATE,
    OFFICIAL_WALK_TEMPLATE,
)
from community.models import Event

URL = "/api/community/event-description-templates/"


@pytest.mark.django_db
class TestGetEventDescriptionTemplates:
    def test_authenticated_user_gets_both_templates(self, api_client, auth_headers):
        response = api_client.get(URL, **auth_headers)
        assert response.status_code == 200
        assert response.json() == {
            "official_walk": OFFICIAL_WALK_TEMPLATE,
            "official_non_walk": OFFICIAL_NON_WALK_TEMPLATE,
        }

    def test_unauthenticated_returns_401(self, api_client):
        assert api_client.get(URL).status_code == 401


@pytest.mark.parametrize("template", [OFFICIAL_WALK_TEMPLATE, OFFICIAL_NON_WALK_TEMPLATE])
def test_templates_fit_event_description(template):
    max_length = Event._meta.get_field("description").max_length
    assert max_length is not None
    assert len(template) <= max_length
