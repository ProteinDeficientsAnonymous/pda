import pytest
from community.models import PlanningSlot, PlanningYear
from community.planning.years import get_year_or_404
from community.validation import Code, ValidationException
from users.permissions import PermissionKey

from tests._asserts import assert_error_code
from tests._auth import auth_headers_for
from tests._users import make_user

BASE = "/api/community/planning"
VIEW = PermissionKey.VIEW_EVENT_PLANNING
MANAGE = PermissionKey.MANAGE_EVENT_PLANNING

VIEW_ROUTES = [("get", f"{BASE}/years/", None)]
MANAGE_ROUTES = [("post", f"{BASE}/years/", {"year": 2028})]


def send(api_client, method, url, body=None, headers=None):
    kwargs = {"data": body, "content_type": "application/json"} if body is not None else {}
    return getattr(api_client, method)(url, **kwargs, **(headers or {}))


def headers_for(*permissions):
    return auth_headers_for(make_user(*permissions))


@pytest.fixture
def year(db):
    return PlanningYear.create_with_default_slots(2027)


@pytest.mark.django_db
class TestAccess:
    @pytest.mark.parametrize(("method", "url", "body"), VIEW_ROUTES + MANAGE_ROUTES)
    def test_unauthenticated(self, api_client, method, url, body):
        assert send(api_client, method, url, body).status_code == 401

    @pytest.mark.parametrize(("method", "url", "body"), VIEW_ROUTES + MANAGE_ROUTES)
    def test_plain_member_forbidden(self, api_client, method, url, body):
        assert send(api_client, method, url, body, headers_for()).status_code == 403

    @pytest.mark.parametrize(("method", "url", "body"), MANAGE_ROUTES)
    def test_view_only_forbidden_on_manage_routes(self, api_client, method, url, body):
        assert send(api_client, method, url, body, headers_for(VIEW)).status_code == 403


@pytest.mark.django_db
class TestYears:
    def test_list_years(self, api_client, year):
        response = send(api_client, "get", f"{BASE}/years/", headers=headers_for(VIEW))
        assert response.status_code == 200
        assert [y["year"] for y in response.json()] == [2027]

    def test_create_year_seeds_default_slots(self, api_client):
        response = send(api_client, "post", f"{BASE}/years/", {"year": 2028}, headers_for(MANAGE))
        assert response.status_code == 201
        assert response.json()["year"] == 2028
        assert PlanningSlot.objects.filter(planning_year__year=2028).count() == 14

    def test_create_duplicate_year(self, api_client, year):
        response = send(api_client, "post", f"{BASE}/years/", {"year": 2027}, headers_for(MANAGE))
        assert response.status_code == 400
        assert_error_code(response, Code.Planning.YEAR_EXISTS, "year")

    def test_create_year_out_of_range(self, api_client):
        response = send(api_client, "post", f"{BASE}/years/", {"year": 1999}, headers_for(MANAGE))
        assert response.status_code == 422

    def test_get_year_or_404(self, year):
        assert get_year_or_404(2027) == year
        with pytest.raises(ValidationException) as exc:
            get_year_or_404(2099)
        assert exc.value.code == Code.Planning.YEAR_NOT_FOUND
        assert exc.value.status_code == 404
