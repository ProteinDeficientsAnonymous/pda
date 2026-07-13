import pytest
from users.models import User


@pytest.mark.django_db
class TestCreateUserDuplicateEmail:
    def test_create_user_duplicate_email_rejected(self, api_client, manage_users_headers, db):
        User.objects.create_user(
            phone_number="+12025550199", first_name="a", email="taken@example.com"
        )
        resp = api_client.post(
            "/api/auth/create-user/",
            data={
                "phone_number": "+12025550101",
                "first_name": "b",
                "email": "Taken@Example.com",
            },
            content_type="application/json",
            **manage_users_headers,
        )
        assert resp.status_code == 409
        assert resp.json()["detail"][0]["code"] == "email.already_exists"

    def test_create_user_lowercases_email(self, api_client, manage_users_headers, db):
        resp = api_client.post(
            "/api/auth/create-user/",
            data={
                "phone_number": "+12025550101",
                "first_name": "b",
                "email": "Foo@Example.com",
            },
            content_type="application/json",
            **manage_users_headers,
        )
        assert resp.status_code == 201, resp.content
        user = User.objects.get(phone_number="+12025550101")
        assert user.email == "foo@example.com"


@pytest.mark.django_db
class TestAdminPatchEmail:
    def test_admin_patch_email_rejects_duplicate(self, api_client, manage_users_headers, db):
        User.objects.create_user(
            phone_number="+12025550199", first_name="other", email="taken@example.com"
        )
        target = User.objects.create_user(phone_number="+12025550101", first_name="b")
        resp = api_client.patch(
            f"/api/auth/users/{target.id}/",
            data={"email": "Taken@Example.com"},
            content_type="application/json",
            **manage_users_headers,
        )
        assert resp.status_code == 409
        assert resp.json()["detail"][0]["code"] == "email.already_exists"

    def test_admin_patch_email_lowercases(self, api_client, manage_users_headers, db):
        target = User.objects.create_user(phone_number="+12025550101", first_name="b")
        resp = api_client.patch(
            f"/api/auth/users/{target.id}/",
            data={"email": "Foo@Example.com"},
            content_type="application/json",
            **manage_users_headers,
        )
        assert resp.status_code == 200
        target.refresh_from_db()
        assert target.email == "foo@example.com"
