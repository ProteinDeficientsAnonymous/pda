import pytest
from community.models import DocFolder, Document
from django.db import connection
from django.test.utils import CaptureQueriesContext

from tests.test_docs import BASE, manage_docs_headers, manage_docs_user  # noqa: F401


def _make_trees(count: int) -> None:
    for i in range(count):
        root = DocFolder.objects.create(name=f"root {i}")
        child = DocFolder.objects.create(name=f"child {i}", parent=root)
        grandchild = DocFolder.objects.create(name=f"grandchild {i}", parent=child)
        for folder in (root, child, grandchild):
            Document.objects.create(title=f"doc in {folder.name}", folder=folder)


def _count(api_client, method: str, url: str, headers: dict, **kwargs) -> int:
    with CaptureQueriesContext(connection) as ctx:
        response = getattr(api_client, method)(url, **kwargs, **headers)
    assert response.status_code == 200
    return len(ctx.captured_queries)


@pytest.mark.django_db
class TestDocsQueryCounts:
    def test_folder_tree_is_constant(self, api_client, manage_docs_headers):  # noqa: F811
        _make_trees(2)
        small = _count(api_client, "get", f"{BASE}/folders/", manage_docs_headers)
        _make_trees(6)
        large = _count(api_client, "get", f"{BASE}/folders/", manage_docs_headers)
        assert large == small

    def test_folder_tree_shape(self, api_client, manage_docs_headers):  # noqa: F811
        _make_trees(1)
        data = api_client.get(f"{BASE}/folders/", **manage_docs_headers).json()
        assert [f["name"] for f in data] == ["root 0"]
        child = data[0]["children"][0]
        assert child["name"] == "child 0"
        assert child["children"][0]["documents"][0]["title"] == "doc in grandchild 0"

    @pytest.mark.parametrize(
        "model,url", [(DocFolder, "/folders/reorder/"), (Document, "/reorder/")]
    )
    def test_reorder_is_constant(self, api_client, manage_docs_headers, model, url):  # noqa: F811
        _make_trees(4)
        ids = [str(pk) for pk in model.objects.values_list("id", flat=True)]

        def reorder(subset: list[str]) -> int:
            return _count(
                api_client,
                "put",
                f"{BASE}{url}",
                manage_docs_headers,
                data={"ids": subset},
                content_type="application/json",
            )

        assert reorder(ids[:2]) == reorder(ids[::-1])
        orders = {str(pk): o for pk, o in model.objects.values_list("id", "display_order")}
        assert [orders[pk] for pk in ids[::-1]] == list(range(len(ids)))
