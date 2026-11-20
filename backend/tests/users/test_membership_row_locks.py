import pytest
from community.validation import Code
from django.db.models.query import QuerySet
from tests._asserts import assert_error_code
from users.models import User


@pytest.mark.django_db
def test_update_user_locks_row_for_update(
    api_client, manage_users_headers, other_user, monkeypatch
):
    original = QuerySet.select_for_update
    called = False

    def spy(self, *args, **kwargs):
        nonlocal called
        called = True
        return original(self, *args, **kwargs)

    monkeypatch.setattr(QuerySet, "select_for_update", spy)
    response = api_client.patch(
        f"/api/auth/users/{other_user.pk}/",
        {"first_name": "Locked"},
        content_type="application/json",
        **manage_users_headers,
    )
    assert response.status_code == 200
    assert called


@pytest.mark.django_db
def test_delete_user_archive_noop_returns_already_archived(
    api_client, manage_users_headers, other_user, monkeypatch
):
    monkeypatch.setattr("users._user_deletion.archive_user", lambda *_a, **_k: {})
    response = api_client.delete(
        f"/api/auth/users/{other_user.pk}/",
        **manage_users_headers,
    )
    assert response.status_code == 400
    assert_error_code(response, Code.User.ALREADY_ARCHIVED)
    assert User.objects.filter(pk=other_user.pk, archived_at__isnull=True).exists()
