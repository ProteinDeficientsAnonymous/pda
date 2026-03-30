import pytest
from users.api import _create_user_with_role, _validate_admin_role_change
from users.permissions import PermissionKey
from users.roles import Role

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def admin_user(db):
    from users.models import User

    user = User.objects.create_superuser(
        phone_number="+12025550001",
        password="adminpass123",
        display_name="Admin User",
    )
    return user


@pytest.fixture
def admin_headers(admin_user):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(admin_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


@pytest.fixture
def manage_users_user(db):
    """A non-superuser with only manage_users permission."""
    from users.models import User

    user = User.objects.create_user(
        phone_number="+12025550002",
        password="managerpass123",
        display_name="Manager",
    )
    role = Role.objects.create(
        name="manager", permissions=[PermissionKey.MANAGE_USERS, PermissionKey.MANAGE_ROLES]
    )
    user.roles.add(role)
    return user


@pytest.fixture
def manage_users_headers(manage_users_user):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(manage_users_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAuth:
    def test_login_valid(self, api_client, test_user):
        response = api_client.post(
            "/api/auth/login/",
            {"phone_number": "+12025550101", "password": "testpass123"},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert "access" in data
        assert "refresh" in data

    def test_login_invalid(self, api_client):
        response = api_client.post(
            "/api/auth/login/",
            {"phone_number": "+19999999999", "password": "wrong"},
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_login_old_email_format_rejected(self, api_client, test_user):
        response = api_client.post(
            "/api/auth/login/",
            {"email": "member@pda.org", "password": "testpass123"},
            content_type="application/json",
        )
        assert response.status_code in (401, 422)

    def test_me_authenticated(self, api_client, test_user, auth_headers):
        response = api_client.get("/api/auth/me/", **auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["phone_number"] == "+12025550101"
        assert data["display_name"] == "Test Member"
        assert "first_name" not in data
        assert "last_name" not in data
        assert "roles" in data

    def test_me_unauthenticated(self, api_client):
        response = api_client.get("/api/auth/me/")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Roles and permissions (model-level)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRolesAndPermissions:
    def test_has_permission_via_role(self, test_user):
        role = Role.objects.get(name="member")
        role.permissions = [PermissionKey.MANAGE_EVENTS]
        role.save()
        test_user.roles.add(role)
        assert test_user.has_permission(PermissionKey.MANAGE_EVENTS)
        assert not test_user.has_permission(PermissionKey.MANAGE_USERS)

    def test_admin_role_grants_all_permissions(self, test_user):
        admin_role = Role.objects.get(name="admin")
        test_user.roles.add(admin_role)
        assert test_user.has_permission(PermissionKey.MANAGE_USERS)
        assert test_user.has_permission(PermissionKey.MANAGE_EVENTS)
        assert test_user.has_permission(PermissionKey.APPROVE_JOIN_REQUESTS)

    def test_no_roles_grants_no_permissions(self, test_user):
        assert not test_user.has_permission(PermissionKey.MANAGE_EVENTS)

    def test_superuser_gets_admin_role_on_create(self, db):
        from users.models import User

        superuser = User.objects.create_superuser(
            phone_number="+12025559999", password="superpass123"
        )
        assert superuser.roles.filter(name="admin").exists()

    def test_has_permission_uses_prefetch_cache(self, test_user):
        from users.models import User

        member_role = Role.objects.get(name="member")
        test_user.roles.add(member_role)
        user = User.objects.prefetch_related("roles").get(pk=test_user.pk)
        assert not user.has_permission(PermissionKey.MANAGE_USERS)


# ---------------------------------------------------------------------------
# User management API (#3)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestUserManagementAPI:
    def test_create_user_requires_permission(self, api_client, auth_headers):
        response = api_client.post(
            "/api/auth/create-user/",
            {"phone_number": "+12025550999"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 403

    def test_create_user_success(self, api_client, admin_headers):
        response = api_client.post(
            "/api/auth/create-user/",
            {"phone_number": "+12025551234", "display_name": "New Member"},
            content_type="application/json",
            **admin_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["phone_number"] == "+12025551234"
        assert "temporary_password" in data
        assert len(data["temporary_password"]) == 16

    def test_create_user_duplicate_phone(self, api_client, admin_headers, test_user):
        response = api_client.post(
            "/api/auth/create-user/",
            {"phone_number": "+12025550101"},
            content_type="application/json",
            **admin_headers,
        )
        assert response.status_code == 400

    def test_create_user_assigns_member_role_by_default(self, api_client, admin_headers):
        response = api_client.post(
            "/api/auth/create-user/",
            {"phone_number": "+12125551234"},
            content_type="application/json",
            **admin_headers,
        )
        assert response.status_code == 201
        from users.models import User

        user = User.objects.get(phone_number="+12125551234")
        assert user.roles.filter(name="member").exists()

    def test_list_users_requires_manage_users(self, api_client, auth_headers):
        response = api_client.get("/api/auth/users/", **auth_headers)
        assert response.status_code == 403

    def test_list_users_success(self, api_client, admin_headers, test_user):
        response = api_client.get("/api/auth/users/", **admin_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_update_user(self, api_client, admin_headers, test_user):
        response = api_client.patch(
            f"/api/auth/users/{test_user.id}/",
            {"display_name": "Updated Name"},
            content_type="application/json",
            **admin_headers,
        )
        assert response.status_code == 200
        assert response.json()["display_name"] == "Updated Name"

    def test_delete_user_cannot_delete_self(self, api_client, admin_headers, admin_user):
        response = api_client.delete(
            f"/api/auth/users/{admin_user.id}/",
            **admin_headers,
        )
        assert response.status_code == 400
        assert "own account" in response.json()["detail"]

    def test_delete_user_cannot_delete_last_admin(
        self, api_client, manage_users_headers, admin_user
    ):
        response = api_client.delete(
            f"/api/auth/users/{admin_user.id}/",
            **manage_users_headers,
        )
        assert response.status_code == 400
        assert "last admin" in response.json()["detail"]

    def test_delete_user_success(self, api_client, admin_headers):
        from users.models import User

        other = User.objects.create_user(phone_number="+12025550888", password="pass123")
        response = api_client.delete(f"/api/auth/users/{other.id}/", **admin_headers)
        assert response.status_code == 204

    def test_update_user_roles_cannot_remove_own_admin(self, api_client, admin_headers, admin_user):
        member_role = Role.objects.get(name="member")
        response = api_client.patch(
            f"/api/auth/users/{admin_user.id}/roles/",
            {"role_ids": [str(member_role.id)]},
            content_type="application/json",
            **admin_headers,
        )
        assert response.status_code == 400
        assert "own admin role" in response.json()["detail"]

    def test_reset_password(self, api_client, admin_headers, test_user):
        response = api_client.post(
            f"/api/auth/users/{test_user.id}/reset-password/",
            **admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "temporary_password" in data
        assert len(data["temporary_password"]) == 16

    def test_reset_password_requires_manage_users(self, api_client, auth_headers, test_user):
        response = api_client.post(
            f"/api/auth/users/{test_user.id}/reset-password/",
            **auth_headers,
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Unit tests for _create_user_with_role helper
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCreateUserWithRole:
    def test_creates_user_with_default_member_role(self):
        Role.objects.get_or_create(name="member", defaults={"is_default": True})
        user, temp_password = _create_user_with_role("+12025559999", "Test User", "t@e.com", None)
        assert user.phone_number == "+12025559999"
        assert len(temp_password) == 16
        assert user.roles.filter(name="member").exists()

    def test_creates_user_with_specific_role(self):
        role = Role.objects.create(name="custom_role")
        user, _ = _create_user_with_role("+12025558888", "Custom User", "c@e.com", str(role.pk))
        assert user.roles.filter(pk=role.pk).exists()

    def test_raises_on_duplicate_phone(self):
        from users.models import User

        User.objects.create_user(phone_number="+12025557777", password="pass123")
        with pytest.raises(ValueError, match="already exists"):
            _create_user_with_role("+12025557777", "Dup", None, None)

    def test_raises_on_invalid_phone(self):
        with pytest.raises(ValueError):
            _create_user_with_role("not-a-phone", "Bad Phone", None, None)

    def test_raises_on_bad_role_and_deletes_user(self):
        from users.models import User

        with pytest.raises(ValueError, match="Role not found"):
            _create_user_with_role(
                "+12025556666", "Bad Role User", "b@e.com", "00000000-0000-0000-0000-000000000000"
            )
        assert not User.objects.filter(phone_number="+12025556666").exists()


# ---------------------------------------------------------------------------
# Unit tests for _validate_admin_role_change
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestValidateAdminRoleChange:
    def test_returns_none_when_no_admin_role_exists(self):
        from users.models import User

        user = User.objects.create_user(phone_number="+12025550101", password="p", email="a@e.com")
        assert _validate_admin_role_change(user, "other-pk", []) is None

    def test_returns_error_when_removing_own_admin(self):
        from users.models import User

        admin_role = Role.objects.get_or_create(name="admin", defaults={"is_default": True})[0]
        member_role = Role.objects.get_or_create(name="member", defaults={"is_default": True})[0]
        user = User.objects.create_user(phone_number="+12025550102", password="p", email="b@e.com")
        user.roles.add(admin_role)
        result = _validate_admin_role_change(user, str(user.pk), [member_role])
        assert result == "You cannot remove your own admin role."

    def test_returns_none_when_keeping_own_admin(self):
        from users.models import User

        admin_role = Role.objects.get_or_create(name="admin", defaults={"is_default": True})[0]
        user = User.objects.create_user(phone_number="+12025550103", password="p", email="c@e.com")
        user.roles.add(admin_role)
        assert _validate_admin_role_change(user, str(user.pk), [admin_role]) is None

    def test_returns_error_when_removing_last_admin(self):
        from users.models import User

        admin_role = Role.objects.get_or_create(name="admin", defaults={"is_default": True})[0]
        member_role = Role.objects.get_or_create(name="member", defaults={"is_default": True})[0]
        user = User.objects.create_user(phone_number="+12025550104", password="p", email="d@e.com")
        user.roles.add(admin_role)
        # Request from a different user (not self-removal)
        result = _validate_admin_role_change(user, "someone-else", [member_role])
        assert result == "Cannot remove admin from the last admin."


# ---------------------------------------------------------------------------
# Role management API (#4)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRoleManagementAPI:
    def test_list_roles_authenticated(self, api_client, auth_headers):
        response = api_client.get("/api/auth/roles/", **auth_headers)
        assert response.status_code == 200
        names = [r["name"] for r in response.json()]
        assert "admin" in names
        assert "member" in names

    def test_list_roles_unauthenticated(self, api_client):
        response = api_client.get("/api/auth/roles/")
        assert response.status_code == 401

    def test_create_role_success(self, api_client, manage_users_headers):
        response = api_client.post(
            "/api/auth/roles/",
            {"name": "vettor", "permissions": ["approve_join_requests"]},
            content_type="application/json",
            **manage_users_headers,
        )
        assert response.status_code == 201
        assert response.json()["name"] == "vettor"

    def test_create_role_requires_manage_roles(self, api_client, auth_headers):
        response = api_client.post(
            "/api/auth/roles/",
            {"name": "newrole"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 403

    def test_create_role_duplicate_name(self, api_client, manage_users_headers):
        response = api_client.post(
            "/api/auth/roles/",
            {"name": "member"},
            content_type="application/json",
            **manage_users_headers,
        )
        assert response.status_code == 400

    def test_patch_role_permissions(self, api_client, manage_users_headers):
        role = Role.objects.create(name="custom", permissions=[])
        response = api_client.patch(
            f"/api/auth/roles/{role.id}/",
            {"permissions": ["manage_events"]},
            content_type="application/json",
            **manage_users_headers,
        )
        assert response.status_code == 200
        assert "manage_events" in response.json()["permissions"]

    def test_patch_protected_role_name_blocked(self, api_client, manage_users_headers):
        admin_role = Role.objects.get(name="admin")
        response = api_client.patch(
            f"/api/auth/roles/{admin_role.id}/",
            {"name": "superadmin"},
            content_type="application/json",
            **manage_users_headers,
        )
        assert response.status_code == 400
        assert "protected" in response.json()["detail"]

    def test_delete_role_success(self, api_client, manage_users_headers):
        role = Role.objects.create(name="deleteme", permissions=[])
        response = api_client.delete(f"/api/auth/roles/{role.id}/", **manage_users_headers)
        assert response.status_code == 204

    def test_delete_protected_role_blocked(self, api_client, manage_users_headers):
        admin_role = Role.objects.get(name="admin")
        response = api_client.delete(f"/api/auth/roles/{admin_role.id}/", **manage_users_headers)
        assert response.status_code == 400
        assert "protected" in response.json()["detail"]

    def test_delete_role_with_users_blocked(self, api_client, manage_users_headers, test_user):
        role = Role.objects.create(name="occupied", permissions=[])
        test_user.roles.add(role)
        response = api_client.delete(f"/api/auth/roles/{role.id}/", **manage_users_headers)
        assert response.status_code == 400
        assert "users assigned" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Join request + email notification (#5)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestJoinRequest:
    @pytest.fixture
    def why_join_id(self, db):
        from community.models import JoinFormQuestion

        q = JoinFormQuestion.objects.filter(required=True).first()
        return str(q.id) if q else ""

    def test_submit_join_request(self, api_client, why_join_id):
        response = api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "Leafy G",
                "phone_number": "+12025551234",
                "answers": {why_join_id: "I want to connect with other vegans."},
            },
            content_type="application/json",
        )
        assert response.status_code == 201
        data = response.json()
        assert data["display_name"] == "Leafy G"
        assert data["phone_number"] == "+12025551234"
        assert len(data["answers"]) >= 1

    def test_submit_join_request_missing_required_answer(self, api_client):
        response = api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "Leafy G",
                "phone_number": "+12025551234",
                "answers": {},
            },
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_submit_join_request_invalid_display_name(self, api_client, why_join_id):
        response = api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "Leafy123",
                "phone_number": "+12025551234",
                "answers": {why_join_id: "Liberation."},
            },
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_submit_join_request_invalid_phone(self, api_client, why_join_id):
        response = api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "Leafy G",
                "phone_number": "not-a-number",
                "answers": {why_join_id: "Liberation."},
            },
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_submit_join_request_optional_answers(self, api_client, why_join_id):
        response = api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "Leafy G",
                "phone_number": "+13105551234",
                "answers": {why_join_id: "Liberation."},
            },
            content_type="application/json",
        )
        assert response.status_code == 201

    def test_join_request_sends_email_when_vetting_email_set(
        self, api_client, settings, why_join_id
    ):
        settings.VETTING_EMAIL = "vetting@pda.org"
        from django.core import mail

        api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "Test Person",
                "phone_number": "+14155551234",
                "answers": {why_join_id: "Because liberation."},
            },
            content_type="application/json",
        )
        assert len(mail.outbox) == 1
        assert "Test Person" in mail.outbox[0].subject
        assert mail.outbox[0].to == ["vetting@pda.org"]

    def test_join_request_no_email_when_vetting_email_unset(
        self, api_client, settings, why_join_id
    ):
        settings.VETTING_EMAIL = ""
        from django.core import mail

        api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "Test Person",
                "phone_number": "+14155551234",
                "answers": {why_join_id: "Because liberation."},
            },
            content_type="application/json",
        )
        assert len(mail.outbox) == 0


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestEvents:
    def test_events_public(self, api_client):
        response = api_client.get("/api/community/events/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_events_authenticated(self, api_client, auth_headers):
        response = api_client.get("/api/community/events/", **auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_events_strips_private_fields_for_anonymous(self, api_client, auth_headers, test_user):
        from community.models import Event
        from django.utils import timezone

        event = Event.objects.create(
            title="Test",
            start_datetime=timezone.now(),
            end_datetime=timezone.now(),
            location="",
            whatsapp_link="https://chat.whatsapp.com/abc",
            partiful_link="https://partiful.com/e/abc",
            rsvp_enabled=False,
            created_by=test_user,
        )
        anon_res = api_client.get("/api/community/events/")
        authed_res = api_client.get("/api/community/events/", **auth_headers)

        anon_event = next(e for e in anon_res.json() if e["id"] == str(event.id))
        authed_event = next(e for e in authed_res.json() if e["id"] == str(event.id))

        assert anon_event["whatsapp_link"] == ""
        assert anon_event["partiful_link"] == ""
        assert authed_event["whatsapp_link"] == "https://chat.whatsapp.com/abc"
        assert authed_event["partiful_link"] == "https://partiful.com/e/abc"


# ---------------------------------------------------------------------------
# Join request management API (#6)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestJoinRequestManagement:
    @pytest.fixture
    def vettor_user(self, db):
        from users.models import User

        user = User.objects.create_user(
            phone_number="+12025550003",
            password="vettorpass123",
            display_name="Vettor",
        )
        role = Role.objects.create(name="vettor", permissions=[PermissionKey.APPROVE_JOIN_REQUESTS])
        user.roles.add(role)
        return user

    @pytest.fixture
    def vettor_headers(self, vettor_user):
        from ninja_jwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(vettor_user)
        return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore

    @pytest.fixture
    def sample_join_request(self, db):
        from community.models import JoinFormQuestion, JoinRequest

        q = JoinFormQuestion.objects.filter(required=True).first()
        answers = {}
        if q:
            answers[str(q.id)] = {"label": q.label, "answer": "I believe in collective liberation."}
        return JoinRequest.objects.create(
            display_name="Sprout Seedling",
            phone_number="+16505551234",
            custom_answers=answers,
        )

    def test_list_join_requests_requires_permission(self, api_client, auth_headers):
        response = api_client.get("/api/community/join-requests/", **auth_headers)
        assert response.status_code == 403

    def test_list_join_requests_unauthenticated(self, api_client):
        response = api_client.get("/api/community/join-requests/")
        assert response.status_code == 401

    def test_list_join_requests_success(self, api_client, vettor_headers, sample_join_request):
        response = api_client.get("/api/community/join-requests/", **vettor_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["display_name"] == "Sprout Seedling"
        assert data[0]["status"] == "pending"

    def test_list_join_requests_admin_can_access(
        self, api_client, admin_headers, sample_join_request
    ):
        response = api_client.get("/api/community/join-requests/", **admin_headers)
        assert response.status_code == 200

    def test_approve_join_request_success(self, api_client, vettor_headers, sample_join_request):
        response = api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": "approved"},
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        assert data["id"] == str(sample_join_request.id)

    def test_approve_join_request_creates_user(
        self, api_client, vettor_headers, sample_join_request
    ):
        from users.models import User

        response = api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": "approved"},
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["temporary_password"] is not None
        assert len(data["temporary_password"]) == 16
        user = User.objects.get(phone_number=sample_join_request.phone_number)
        assert user.display_name == "Sprout Seedling"
        assert user.needs_onboarding is True
        assert user.roles.filter(name="member").exists()

    def test_reject_join_request_success(self, api_client, vettor_headers, sample_join_request):
        response = api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": "rejected"},
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "rejected"

    def test_update_join_request_status_persists(
        self, api_client, vettor_headers, sample_join_request
    ):
        api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": "approved"},
            content_type="application/json",
            **vettor_headers,
        )
        sample_join_request.refresh_from_db()
        assert sample_join_request.status == "approved"

    def test_update_join_request_invalid_status(
        self, api_client, vettor_headers, sample_join_request
    ):
        response = api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": "pending"},
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 400

    def test_update_join_request_requires_permission(
        self, api_client, auth_headers, sample_join_request
    ):
        response = api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": "approved"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 403

    def test_update_join_request_unauthenticated(self, api_client, sample_join_request):
        response = api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": "approved"},
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_update_join_request_not_found(self, api_client, vettor_headers):
        import uuid

        response = api_client.patch(
            f"/api/community/join-requests/{uuid.uuid4()}/",
            {"status": "approved"},
            content_type="application/json",
            **vettor_headers,
        )
        assert response.status_code == 404

    def test_submit_join_request_default_status_is_pending(self, api_client):
        from community.models import JoinFormQuestion

        q = JoinFormQuestion.objects.filter(required=True).first()
        answers = {str(q.id): "Collective liberation matters."} if q else {}
        response = api_client.post(
            "/api/community/join-request/",
            {
                "display_name": "New Sprout",
                "phone_number": "+19175551234",
                "answers": answers,
            },
            content_type="application/json",
        )
        assert response.status_code == 201
        assert response.json()["status"] == "pending"
