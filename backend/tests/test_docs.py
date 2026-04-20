import pytest
from community.models import DocFolder, Document
from users.permissions import PermissionKey
from users.roles import Role


@pytest.fixture
def manage_docs_user(db):
    from users.models import User

    user = User.objects.create_user(
        phone_number="+15550003001",
        password="docspass123",
        display_name="Docs Manager",
    )
    role = Role.objects.create(name="docs_manager", permissions=[PermissionKey.MANAGE_DOCUMENTS])
    user.roles.add(role)
    return user


@pytest.fixture
def manage_docs_headers(manage_docs_user):
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(manage_docs_user)
    return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}  # ty: ignore[unresolved-attribute]


@pytest.fixture
def folder(db):
    return DocFolder.objects.create(name="recipes")


@pytest.fixture
def document(folder, manage_docs_user):
    return Document.objects.create(
        title="tofu scramble",
        content='[{"insert":"Scramble the tofu.\\n"}]',
        folder=folder,
        created_by=manage_docs_user,
    )


BASE = "/api/community/docs"


@pytest.mark.django_db
class TestDocFolders:
    def test_list_folders(self, api_client, manage_docs_headers, folder):
        response = api_client.get(f"{BASE}/folders/", **manage_docs_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "recipes"

    def test_create_folder(self, api_client, manage_docs_headers):
        response = api_client.post(
            f"{BASE}/folders/",
            data={"name": "guides"},
            content_type="application/json",
            **manage_docs_headers,
        )
        assert response.status_code == 201
        assert response.json()["name"] == "guides"
        assert DocFolder.objects.filter(name="guides").exists()

    def test_create_subfolder(self, api_client, manage_docs_headers, folder):
        response = api_client.post(
            f"{BASE}/folders/",
            data={"name": "breakfast", "parent_id": str(folder.id)},
            content_type="application/json",
            **manage_docs_headers,
        )
        assert response.status_code == 201
        assert response.json()["parent_id"] == str(folder.id)

    def test_create_folder_permission_denied(self, api_client, auth_headers):
        response = api_client.post(
            f"{BASE}/folders/",
            data={"name": "nope"},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 403

    def test_update_folder(self, api_client, manage_docs_headers, folder):
        response = api_client.patch(
            f"{BASE}/folders/{folder.id}/",
            data={"name": "cookbooks"},
            content_type="application/json",
            **manage_docs_headers,
        )
        assert response.status_code == 200
        assert response.json()["name"] == "cookbooks"

    def test_delete_folder(self, api_client, manage_docs_headers, folder):
        response = api_client.delete(
            f"{BASE}/folders/{folder.id}/",
            **manage_docs_headers,
        )
        assert response.status_code == 200
        assert not DocFolder.objects.filter(pk=folder.id).exists()

    def test_reorder_folders(self, api_client, manage_docs_headers):
        f1 = DocFolder.objects.create(name="a")
        f2 = DocFolder.objects.create(name="b")
        response = api_client.put(
            f"{BASE}/folders/reorder/",
            data={"ids": [str(f2.id), str(f1.id)]},
            content_type="application/json",
            **manage_docs_headers,
        )
        assert response.status_code == 200
        f1.refresh_from_db()
        f2.refresh_from_db()
        assert f2.display_order == 0
        assert f1.display_order == 1


@pytest.mark.django_db
class TestDocuments:
    def test_get_document(self, api_client, manage_docs_headers, document):
        response = api_client.get(f"{BASE}/{document.id}/", **manage_docs_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "tofu scramble"
        assert data["content"] == document.content

    def test_create_document(self, api_client, manage_docs_headers, folder):
        response = api_client.post(
            f"{BASE}/",
            data={"title": "tempeh tacos", "folder_id": str(folder.id)},
            content_type="application/json",
            **manage_docs_headers,
        )
        assert response.status_code == 201
        assert response.json()["title"] == "tempeh tacos"

    def test_create_document_permission_denied(self, api_client, auth_headers, folder):
        response = api_client.post(
            f"{BASE}/",
            data={"title": "nope", "folder_id": str(folder.id)},
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 403

    def test_update_document(self, api_client, manage_docs_headers, document):
        response = api_client.patch(
            f"{BASE}/{document.id}/",
            data={"title": "the best tofu scramble"},
            content_type="application/json",
            **manage_docs_headers,
        )
        assert response.status_code == 200
        assert response.json()["title"] == "the best tofu scramble"

    def test_delete_document(self, api_client, manage_docs_headers, document):
        response = api_client.delete(
            f"{BASE}/{document.id}/",
            **manage_docs_headers,
        )
        assert response.status_code == 200
        assert not Document.objects.filter(pk=document.id).exists()

    def test_reorder_documents(self, api_client, manage_docs_headers, folder):
        d1 = Document.objects.create(title="a", folder=folder)
        d2 = Document.objects.create(title="b", folder=folder)
        response = api_client.put(
            f"{BASE}/reorder/",
            data={"ids": [str(d2.id), str(d1.id)]},
            content_type="application/json",
            **manage_docs_headers,
        )
        assert response.status_code == 200
        d1.refresh_from_db()
        d2.refresh_from_db()
        assert d2.display_order == 0
        assert d1.display_order == 1

    def test_read_access_regular_member_denied(self, api_client, auth_headers, document):
        """Docs are admin-only: regular members get 403 on read."""
        response = api_client.get(f"{BASE}/{document.id}/", **auth_headers)
        assert response.status_code == 403

    def test_list_folders_regular_member_denied(self, api_client, auth_headers, folder):
        """Docs are admin-only: regular members get 403 listing folders."""
        response = api_client.get(f"{BASE}/folders/", **auth_headers)
        assert response.status_code == 403
