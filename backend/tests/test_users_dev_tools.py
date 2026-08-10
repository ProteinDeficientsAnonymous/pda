import pytest
from ninja_jwt.tokens import RefreshToken
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role


@pytest.fixture
def dev_tools_user(db):
    user = User.objects.create_user(
        phone_number="+15550004004",
        password="devtoolsuserpass123",
        first_name="Dev",
        last_name="Tools",
        is_member=True,
    )
    role = Role.objects.create(name="user_manager", permissions=[PermissionKey.MANAGE_USERS])
    user.roles.add(role)
    return user


@pytest.fixture
def dev_tools_headers(dev_tools_user):
    refresh = RefreshToken.for_user(dev_tools_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.mark.django_db
class TestCreateDevTestUser:
    def test_create_default_uses_default_password_and_consents(
        self, api_client, dev_tools_headers, monkeypatch
    ):
        monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
        response = api_client.post(
            "/api/auth/dev/test-users/",
            data={},
            content_type="application/json",
            **dev_tools_headers,
        )
        assert response.status_code == 201
        body = response.json()
        assert body["password"] == "testPassword1@"

        user = User.objects.get(id=body["id"])
        assert user.check_password("testPassword1@")
        assert user.is_member is True
        assert user.guidelines_consent_at is not None
        assert user.sms_consent_at is not None
        assert user.contact_privacy_consent_at is not None
        assert user.archived_at is None
        assert user.is_paused is False

    def test_create_with_overrides(self, api_client, dev_tools_headers, monkeypatch):
        monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
        response = api_client.post(
            "/api/auth/dev/test-users/",
            data={
                "password": "customPass1@",
                "is_member": False,
                "is_paused": True,
                "is_archived": True,
                "guidelines_consent": False,
                "sms_consent": False,
                "contact_privacy_consent": False,
            },
            content_type="application/json",
            **dev_tools_headers,
        )
        assert response.status_code == 201
        user = User.objects.get(id=response.json()["id"])
        assert user.check_password("customPass1@")
        assert user.is_member is False
        assert user.is_paused is True
        assert user.archived_at is not None
        assert user.guidelines_consent_at is None
        assert user.sms_consent_at is None
        assert user.contact_privacy_consent_at is None

    def test_requires_manage_users_permission(self, api_client, monkeypatch):
        monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
        user = User.objects.create_user(
            phone_number="+15550004005",
            password="nopermspass123",
            first_name="No",
            last_name="Perms",
            is_member=True,
        )
        refresh = RefreshToken.for_user(user)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore
        response = api_client.post(
            "/api/auth/dev/test-users/",
            data={},
            content_type="application/json",
            **headers,
        )
        assert response.status_code == 404
