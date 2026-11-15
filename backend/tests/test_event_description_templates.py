import pytest
from community.events.description_templates import (
    CLUB_TEMPLATE,
    HOW_TO_SHOW_UP,
    OFFICIAL_NON_WALK_TEMPLATE,
    OFFICIAL_WALK_TEMPLATE,
)
from community.field_limits import FieldLimit

URL = "/api/community/event-description-templates/"


@pytest.mark.django_db
class TestGetEventDescriptionTemplates:
    def test_authenticated_user_gets_all_templates(self, api_client, auth_headers):
        response = api_client.get(URL, **auth_headers)
        assert response.status_code == 200
        assert response.json() == {
            "official_walk": OFFICIAL_WALK_TEMPLATE,
            "official_non_walk": OFFICIAL_NON_WALK_TEMPLATE,
            "club": CLUB_TEMPLATE,
        }

    def test_unauthenticated_returns_401(self, api_client):
        assert api_client.get(URL).status_code == 401


ALL_TEMPLATES = [OFFICIAL_WALK_TEMPLATE, OFFICIAL_NON_WALK_TEMPLATE, CLUB_TEMPLATE]


@pytest.mark.parametrize("template", ALL_TEMPLATES)
def test_templates_fit_event_description(template):
    assert len(template) <= FieldLimit.EVENT_DESCRIPTION


@pytest.mark.parametrize("template", ALL_TEMPLATES)
def test_templates_include_how_to_show_up(template):
    assert HOW_TO_SHOW_UP in template
