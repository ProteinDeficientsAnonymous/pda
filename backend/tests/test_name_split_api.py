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

    def test_full_name_after_save(self):
        u = User.objects.create_user(
            phone_number="+15551230003", first_name="Ada", last_name="Lovelace"
        )
        u.refresh_from_db()
        assert u.full_name == "Ada Lovelace"

    def test_full_name_reflects_updated_names(self):
        u = User.objects.create_user(
            phone_number="+15551239500", first_name="Ada", last_name="Lovelace"
        )
        u.first_name = "Grace"
        u.last_name = "Hopper"
        u.save(update_fields=["first_name", "last_name"])
        u.refresh_from_db()
        assert u.full_name == "Grace Hopper"

    def test_full_name_empty_when_names_blanked(self):
        u = User.objects.create_user(
            phone_number="+15551239700", first_name="Ada", last_name="Lovelace"
        )
        u.refresh_from_db()
        assert u.full_name == "Ada Lovelace"
        u.first_name = ""
        u.last_name = ""
        u.save(update_fields=["first_name", "last_name"])
        u.refresh_from_db()
        assert u.full_name == ""


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
        assert u.full_name == "Grace Hopper"


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
    def test_patch_first_and_last_updates_full_name(self, api_client, auth_headers, test_user):
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
        assert body["full_name"] == "Grace Hopper"
        test_user.refresh_from_db()
        assert (test_user.first_name, test_user.last_name) == ("Grace", "Hopper")
        assert test_user.full_name == "Grace Hopper"

    def test_patch_blank_last_name_clears_it_without_422(self, api_client, auth_headers, test_user):
        test_user.first_name = "Ada"
        test_user.last_name = "Lovelace"
        test_user.save(update_fields=["first_name", "last_name"])
        resp = api_client.patch(
            "/api/auth/me/",
            data={"first_name": "Ada", "last_name": ""},
            content_type="application/json",
            **auth_headers,
        )
        assert resp.status_code == 200
        test_user.refresh_from_db()
        assert test_user.last_name == ""
        assert test_user.first_name == "Ada"

    def test_patch_blank_first_name_still_raises_required(self, api_client, auth_headers):
        resp = api_client.patch(
            "/api/auth/me/",
            data={"first_name": "", "last_name": "Lovelace"},
            content_type="application/json",
            **auth_headers,
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert any(e["field"] == "first_name" for e in detail)

    def test_patch_last_name_only_on_empty_first_name_is_rejected(
        self, api_client, needs_onboarding_user, needs_onboarding_auth_headers
    ):
        # A last-name-only patch may not leave an empty first_name in place
        # (the record would remain invalid under the new model, Issue 733).
        resp = api_client.patch(
            "/api/auth/me/",
            data={"last_name": "Lovelace"},
            content_type="application/json",
            **needs_onboarding_auth_headers,
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert any(e["field"] == "first_name" for e in detail)
        needs_onboarding_user.refresh_from_db()
        assert needs_onboarding_user.first_name == ""


@pytest.mark.django_db
class TestUserOutSchema:
    def test_user_out_includes_name_fields(self):
        from users.schemas import UserOut

        u = User.objects.create_user(
            phone_number="+15551230200", first_name="Ada", last_name="Lovelace"
        )
        out = UserOut.from_user(u)
        assert out.first_name == "Ada"
        assert out.last_name == "Lovelace"
        assert out.full_name == "Ada Lovelace"


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
        assert u.full_name == "Grace Hopper"

    def test_nameless_request_rejected_on_create(self, manage_users_user):
        from community._join_request_approval import _provision_approved_user
        from community._validation import ValidationException
        from community.models.join_form import JoinRequest

        jr = JoinRequest.objects.create(phone_number="+12025551214")
        with pytest.raises(ValidationException):
            _provision_approved_user(jr, manage_users_user)

    def test_nameless_request_rejected_on_promote(self, manage_users_user):
        from community._join_request_approval import _provision_approved_user
        from community._validation import ValidationException
        from community.models.join_form import JoinRequest

        non_member = User.objects.create_user(
            phone_number="+12025551215", first_name="Prior", is_member=False
        )
        non_member.first_name = ""
        non_member.save(update_fields=["first_name"])
        jr = JoinRequest.objects.create(phone_number="+12025551215", user=non_member)
        with pytest.raises(ValidationException):
            _provision_approved_user(jr, manage_users_user)

    def test_nameless_request_rejected_on_reactivate(self, manage_users_user):
        from community._join_request_approval import _provision_approved_user
        from community._validation import ValidationException
        from community.models.join_form import JoinRequest
        from django.utils import timezone

        archived = User.objects.create_user(phone_number="+12025551216", first_name="Prior")
        archived.archived_at = timezone.now()
        archived.first_name = ""
        archived.save(update_fields=["archived_at", "first_name"])
        jr = JoinRequest.objects.create(phone_number="+12025551216")
        with pytest.raises(ValidationException):
            _provision_approved_user(jr, manage_users_user)


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
