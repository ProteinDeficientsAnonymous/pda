import pytest
from community.models import JoinRequestStatus
from users.models import User


@pytest.mark.django_db
class TestJoinRequestWhatsapp:
    def test_list_reports_whether_approved_user_joined_whatsapp(
        self, api_client, vettor_headers, sample_join_request
    ):
        api_client.patch(
            f"/api/community/join-requests/{sample_join_request.id}/",
            {"status": JoinRequestStatus.APPROVED},
            content_type="application/json",
            **vettor_headers,
        )
        user = User.objects.get(phone_number=sample_join_request.phone_number)
        user.has_joined_whatsapp = True
        user.save(update_fields=["has_joined_whatsapp"])

        response = api_client.get("/api/community/join-requests/", **vettor_headers)
        assert response.status_code == 200
        items = {r["id"]: r for r in response.json()}
        assert items[str(sample_join_request.id)]["user_has_joined_whatsapp"] is True
