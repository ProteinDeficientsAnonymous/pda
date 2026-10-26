"""Tests for join-form question admin endpoints (CRUD + reorder)."""

import json

import pytest
from community.models import JoinFormQuestion, JoinFormQuestionType, QuestionType
from django.db import connection
from django.test.utils import CaptureQueriesContext
from users.permissions import PermissionKey

from tests._auth import auth_headers_for
from tests._users import make_user


@pytest.fixture
def form_admin_user(db):
    return make_user(PermissionKey.EDIT_JOIN_QUESTIONS)


@pytest.fixture
def form_admin_headers(form_admin_user):
    return auth_headers_for(form_admin_user)


def _make_questions(count: int) -> list[JoinFormQuestion]:
    return [
        JoinFormQuestion.objects.create(
            label=f"Q{i}",
            field_type=JoinFormQuestionType.TEXT,
            display_order=i,
        )
        for i in range(count)
    ]


@pytest.mark.unit
def test_question_type_enums_match_canonical_definitions():
    catalog = {
        question_type.name: (question_type.value, question_type.label)
        for question_type in QuestionType
    }
    join = {
        question_type.name: (question_type.value, question_type.label)
        for question_type in JoinFormQuestionType
    }

    assert join == {name: catalog[name] for name in ("TEXT", "TEXTAREA", "SELECT")}
    assert [question_type.value for question_type in JoinFormQuestionType] == [
        "text",
        "textarea",
        "select",
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

    def test_reorder_query_count_is_constant(self, api_client, form_admin_headers):
        def reorder_queries() -> int:
            ids = [str(q.id) for q in JoinFormQuestion.objects.order_by("-display_order")]
            with CaptureQueriesContext(connection) as ctx:
                response = api_client.put(
                    "/api/community/join-form/questions/order/",
                    data=json.dumps({"question_ids": ids}),
                    content_type="application/json",
                    **form_admin_headers,
                )
            assert response.status_code == 200
            return len(ctx.captured_queries)

        _make_questions(2)
        small = reorder_queries()
        _make_questions(6)
        large = reorder_queries()
        assert large == small

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
class TestJoinFormQuestionTypes:
    def test_create_textarea_question(self, api_client, form_admin_headers):
        response = api_client.post(
            "/api/community/join-form/questions/",
            data=json.dumps(
                {
                    "label": "Why join?",
                    "field_type": JoinFormQuestionType.TEXTAREA,
                    "options": [],
                    "required": True,
                }
            ),
            content_type="application/json",
            **form_admin_headers,
        )
        assert response.status_code == 201
        body = response.json()
        assert body["field_type"] == JoinFormQuestionType.TEXTAREA
        assert (
            JoinFormQuestion.objects.get(id=body["id"]).field_type == JoinFormQuestionType.TEXTAREA
        )

    def test_create_select_question(self, api_client, form_admin_headers):
        response = api_client.post(
            "/api/community/join-form/questions/",
            data=json.dumps(
                {
                    "label": "Heard how?",
                    "field_type": JoinFormQuestionType.SELECT,
                    "options": ["friend", "flyer"],
                    "required": False,
                }
            ),
            content_type="application/json",
            **form_admin_headers,
        )
        assert response.status_code == 201
        assert response.json()["field_type"] == JoinFormQuestionType.SELECT
        assert response.json()["options"] == ["friend", "flyer"]
