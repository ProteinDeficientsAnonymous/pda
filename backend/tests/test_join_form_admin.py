"""Tests for join-form question admin endpoints (CRUD + reorder)."""

import json

import pytest
from community.models import JoinFormQuestion, JoinFormQuestionType
from ninja_jwt.tokens import RefreshToken
from users.models import User
from users.permissions import PermissionKey
from users.roles import Role


@pytest.fixture
def form_admin_user(db):
    user = User.objects.create_user(
        phone_number="+12025550555",
        password="adminpass123",
        first_name="Form",
        last_name="Admin",
    )
    role = Role.objects.create(
        name="form_admin",
        permissions=[PermissionKey.EDIT_JOIN_QUESTIONS],
    )
    user.roles.add(role)
    return user


@pytest.fixture
def form_admin_headers(form_admin_user):
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


@pytest.mark.django_db
class TestJoinFormQuestionRows:
    def test_create_text_question_with_rows(self, api_client, form_admin_headers):
        response = api_client.post(
            "/api/community/join-form/questions/",
            data=json.dumps(
                {
                    "label": "Why join?",
                    "field_type": JoinFormQuestionType.TEXT,
                    "options": [],
                    "required": True,
                    "rows": 5,
                }
            ),
            content_type="application/json",
            **form_admin_headers,
        )
        assert response.status_code == 201
        body = response.json()
        assert body["rows"] == 5
        assert JoinFormQuestion.objects.get(id=body["id"]).rows == 5

    def test_create_select_forces_rows_to_one(self, api_client, form_admin_headers):
        response = api_client.post(
            "/api/community/join-form/questions/",
            data=json.dumps(
                {
                    "label": "Heard how?",
                    "field_type": JoinFormQuestionType.SELECT,
                    "options": ["friend", "flyer"],
                    "required": False,
                    "rows": 5,
                }
            ),
            content_type="application/json",
            **form_admin_headers,
        )
        assert response.status_code == 201
        assert response.json()["rows"] == 1

    def test_update_rows(self, api_client, form_admin_headers):
        q = JoinFormQuestion.objects.create(
            label="Notes",
            field_type=JoinFormQuestionType.TEXT,
            display_order=0,
            rows=1,
        )
        response = api_client.patch(
            f"/api/community/join-form/questions/{q.id}/",
            data=json.dumps(
                {
                    "label": "Notes",
                    "field_type": JoinFormQuestionType.TEXT,
                    "options": [],
                    "required": False,
                    "rows": 8,
                }
            ),
            content_type="application/json",
            **form_admin_headers,
        )
        assert response.status_code == 200
        assert response.json()["rows"] == 8
        q.refresh_from_db()
        assert q.rows == 8

    def test_list_includes_rows(self, api_client):
        JoinFormQuestion.objects.create(
            label="Why?",
            field_type=JoinFormQuestionType.TEXT,
            display_order=0,
            rows=5,
        )
        response = api_client.get("/api/community/join-form/")
        assert response.status_code == 200
        assert response.json()[0]["rows"] == 5
