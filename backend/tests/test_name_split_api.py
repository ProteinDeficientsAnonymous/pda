import pytest
from users.models import User


@pytest.mark.django_db
class TestUserFullName:
    def test_full_name_combines_first_last(self):
        u = User.objects.create_user(
            phone_number="+15551230001", first_name="Ada", last_name="Lovelace"
        )
        assert u.full_name == "Ada Lovelace"

    def test_full_name_first_only(self):
        u = User.objects.create_user(phone_number="+15551230002", first_name="Cher")
        assert u.full_name == "Cher"

    def test_save_syncs_display_name(self):
        u = User.objects.create_user(
            phone_number="+15551230003", first_name="Ada", last_name="Lovelace"
        )
        u.refresh_from_db()
        assert u.display_name == "Ada Lovelace"

    def test_save_with_restricted_update_fields_still_syncs_display_name(self):
        u = User.objects.create_user(
            phone_number="+15551239500", first_name="Ada", last_name="Lovelace"
        )
        u.first_name = "Grace"
        u.last_name = "Hopper"
        u.save(update_fields=["first_name", "last_name"])
        u.refresh_from_db()
        assert u.display_name == "Grace Hopper"


@pytest.mark.django_db
class TestBackfillParsing:
    """The backfill logic (parse_display_name) applied to representative names."""

    def test_backfill_maps_existing_names(self):
        from users._name_parsing import parse_display_name

        u = User.objects.create_user(phone_number="+15551230100", first_name="x")
        u.first_name, u.last_name = parse_display_name("Grace Hopper")
        u.save()
        u.refresh_from_db()
        assert (u.first_name, u.last_name) == ("Grace", "Hopper")
        assert u.display_name == "Grace Hopper"


@pytest.mark.django_db
class TestJoinRequestNames:
    def test_join_request_full_name(self):
        from community.models.join_form import JoinRequest

        jr = JoinRequest.objects.create(
            first_name="Ada", last_name="Lovelace", phone_number="+15551239999"
        )
        assert jr.full_name == "Ada Lovelace"


@pytest.mark.django_db
class TestPatchMeNameFields:
    def test_patch_first_and_last_updates_display_name(self, api_client, auth_headers, test_user):
        resp = api_client.patch(
            "/api/auth/me/",
            data={"first_name": "Grace", "last_name": "Hopper"},
            content_type="application/json",
            **auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["first_name"] == "Grace"
        assert body["last_name"] == "Hopper"
        assert body["display_name"] == "Grace Hopper"
        test_user.refresh_from_db()
        assert (test_user.first_name, test_user.last_name) == ("Grace", "Hopper")
        assert test_user.display_name == "Grace Hopper"

    def test_patch_legacy_display_name_splits_into_first_last(
        self, api_client, auth_headers, test_user
    ):
        resp = api_client.patch(
            "/api/auth/me/",
            data={"display_name": "Ada Lovelace"},
            content_type="application/json",
            **auth_headers,
        )
        assert resp.status_code == 200
        test_user.refresh_from_db()
        assert (test_user.first_name, test_user.last_name) == ("Ada", "Lovelace")
        assert test_user.display_name == "Ada Lovelace"


@pytest.mark.django_db
class TestUserOutSchema:
    def test_user_out_includes_new_and_legacy_names(self):
        from users.schemas import UserOut

        u = User.objects.create_user(
            phone_number="+15551230200", first_name="Ada", last_name="Lovelace"
        )
        out = UserOut.from_user(u)
        assert out.first_name == "Ada"
        assert out.last_name == "Lovelace"
        assert out.full_name == "Ada Lovelace"
        assert out.display_name == "Ada Lovelace"  # transitional


@pytest.mark.django_db
class TestApprovalCopiesNames:
    def test_new_user_gets_first_last_from_join_request(self, manage_users_user):
        from community._join_request_approval import _provision_approved_user
        from community.models.join_form import JoinRequest

        jr = JoinRequest.objects.create(
            first_name="Grace", last_name="Hopper", phone_number="+12025551212"
        )
        token, created = _provision_approved_user(jr, manage_users_user)
        assert created is True
        u = User.objects.get(phone_number="+12025551212")
        assert (u.first_name, u.last_name) == ("Grace", "Hopper")
        assert u.display_name == "Grace Hopper"


@pytest.mark.django_db
class TestNameValidationErrorFields:
    def test_invalid_first_name_error_field_is_first_name_not_display_name(
        self, api_client, auth_headers
    ):
        resp = api_client.patch(
            "/api/auth/me/",
            {"first_name": "Ada1"},
            content_type="application/json",
            **auth_headers,
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert isinstance(detail, list)
        assert any(e["field"] == "first_name" for e in detail), (
            f"expected error with field='first_name' but got fields: {[e.get('field') for e in detail]}"
        )
        assert not any(e["field"] == "display_name" for e in detail), (
            "error should not be attributed to display_name"
        )

    def test_invalid_last_name_error_field_is_last_name_not_display_name(
        self, api_client, auth_headers
    ):
        resp = api_client.patch(
            "/api/auth/me/",
            {"last_name": "Hopper2"},
            content_type="application/json",
            **auth_headers,
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert isinstance(detail, list)
        assert any(e["field"] == "last_name" for e in detail), (
            f"expected error with field='last_name' but got fields: {[e.get('field') for e in detail]}"
        )
        assert not any(e["field"] == "display_name" for e in detail), (
            "error should not be attributed to display_name"
        )
