"""Tests for join-form question admin endpoints (CRUD + reorder)."""

import json

import pytest
from community.models import JoinFormQuestion, JoinFormQuestionType
from users.permissions import PermissionKey
from users.roles import Role


@pytest.fixture
def form_admin_user(db):
    from users.models import User

    user = User.objects.create_user(
        phone_number="+12025550555",
        password="adminpass123",
        display_name="Form Admin",
    )
    role = Role.objects.create(
        name="form_admin",
        permissions=[PermissionKey.EDIT_JOIN_QUESTIONS],
    )
    user.roles.add(role)
    return user


@pytest.fixture
def form_admin_headers(form_admin_user):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(form_admin_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # type: ignore


def _make_questions(count: int) -> list[JoinFormQuestion]:
    return [
        JoinFormQuestion.objects.create(
            label=f"Q{i}",
            field_type=JoinFormQuestionType.TEXT,
            display_order=i,
        )
        for i in range(count)
    ]


@pytest.mark.django_db
class TestReorderJoinFormQuestions:
    def test_reorder_updates_display_order(self, api_client, form_admin_headers):
        qs = _make_questions(3)
        new_order = [str(qs[2].id), str(qs[0].id), str(qs[1].id)]
        response = api_client.put(
            "/api/community/join-form/questions/order/",
            data=json.dumps({"question_ids": new_order}),
            content_type="application/json",
            **form_admin_headers,
        )
        assert response.status_code == 200
        # Re-read from db; check display_order matches new position.
        for idx, qid in enumerate(new_order):
            assert JoinFormQuestion.objects.get(id=qid).display_order == idx

    def test_reorder_requires_permission(self, api_client, auth_headers):
        qs = _make_questions(2)
        response = api_client.put(
            "/api/community/join-form/questions/order/",
            data=json.dumps({"question_ids": [str(qs[1].id), str(qs[0].id)]}),
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 403

    def test_reorder_unauthenticated(self, api_client):
        qs = _make_questions(2)
        response = api_client.put(
            "/api/community/join-form/questions/order/",
            data=json.dumps({"question_ids": [str(qs[1].id), str(qs[0].id)]}),
            content_type="application/json",
        )
        assert response.status_code == 401
