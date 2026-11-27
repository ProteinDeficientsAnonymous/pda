import uuid

import pytest
from audit.models import AuditLogEntry
from community.models import Club
from community.validation import Code
from users.permissions import PermissionKey
from users.roles import Role

from tests._asserts import assert_error_code
from tests._auth import auth_headers_for
from tests._users import make_user

URL = "/api/community/clubs/"


def _put(api_client, headers, club, user_ids):
    ids = [str(i) for i in user_ids]
    return api_client.put(
        f"{URL}{club.id}/reps/", {"user_ids": ids}, content_type="application/json", **headers
    )


@pytest.fixture
def club(db):
    return Club.objects.create(name="book club")


@pytest.mark.django_db
class TestClubReps:
    def test_put_replaces_reps_and_returns_them(self, api_client, manage_events_headers, club):
        a, b = make_user(), make_user()
        _put(api_client, manage_events_headers, club, [a.id, b.id])

        response = _put(api_client, manage_events_headers, club, [b.id])

        assert response.status_code == 200
        assert set(club.reps.all()) == {b}
        assert response.json()["reps"][0]["id"] == str(b.id)

    def test_put_dedupes_ids(self, api_client, manage_events_headers, club):
        a = make_user()
        response = _put(api_client, manage_events_headers, club, [a.id, a.id])
        assert response.status_code == 200
        assert club.reps.count() == 1

    def test_put_rejects_non_member_and_unknown_ids(self, api_client, manage_events_headers, club):
        keep = make_user()
        archived = make_user()
        archived.save(update_fields=archived.archive(by=None))
        club.reps.set([keep])

        for bad in (archived.id, uuid.uuid4()):
            response = _put(api_client, manage_events_headers, club, [keep.id, bad])
            assert response.status_code == 400
            assert_error_code(response, Code.Club.REP_NOT_ELIGIBLE, "user_ids")

        assert set(club.reps.all()) == {keep}

    def test_put_keeps_existing_archived_rep_while_adding(
        self, api_client, manage_events_headers, club
    ):
        a, b = make_user(), make_user()
        club.reps.set([a])
        a.save(update_fields=a.archive(by=None))

        response = _put(api_client, manage_events_headers, club, [a.id, b.id])

        assert response.status_code == 200
        assert set(club.reps.all()) == {a, b}

    def test_put_requires_manage_events(self, api_client, club):
        member = make_user()
        response = _put(api_client, auth_headers_for(member), club, [member.id])
        assert response.status_code == 403

    def test_get_requires_manage_events(self, api_client):
        response = api_client.get(f"{URL}reps/", **auth_headers_for(make_user()))
        assert response.status_code == 403

    def test_put_unknown_club_404(self, api_client, manage_events_headers):
        response = api_client.put(
            f"{URL}{uuid.uuid4()}/reps/",
            {"user_ids": []},
            content_type="application/json",
            **manage_events_headers,
        )
        assert response.status_code == 404

    def test_get_lists_every_club_with_its_reps(self, api_client, manage_events_headers, club):
        other = Club.objects.create(name="movie club")
        a = make_user(first_name="zed")
        b = make_user(first_name="amy")
        club.reps.set([a, b])

        response = api_client.get(f"{URL}reps/", **manage_events_headers)

        by_club = {r["club_id"]: r["reps"] for r in response.json()}
        assert [r["id"] for r in by_club[str(club.id)]] == [str(b.id), str(a.id)]
        assert by_club[str(other.id)] == []

    def test_put_audits_added_and_removed_ids(
        self, api_client, manage_events_headers, club, django_capture_on_commit_callbacks
    ):
        a, b = make_user(), make_user()
        club.reps.set([a])

        with django_capture_on_commit_callbacks(execute=True):
            _put(api_client, manage_events_headers, club, [b.id])

        entry = AuditLogEntry.objects.get(action="club_reps_updated", target_id=str(club.id))
        assert entry.details == {"name": club.name, "added": [str(b.id)], "removed": [str(a.id)]}

    def test_public_club_list_has_no_reps(self, api_client, club):
        club.reps.set([make_user()])
        items = api_client.get(URL).json()
        assert all(set(item) == {"id", "name", "requirements"} for item in items)


@pytest.mark.django_db
class TestClubRepPrivacy:
    def test_hidden_phone_is_blanked(self, api_client, manage_events_headers, club):
        rep = make_user(show_phone=False)
        club.reps.set([rep])

        response = api_client.get(f"{URL}reps/", **manage_events_headers)

        assert response.json()[0]["reps"][0]["phone_number"] == ""

    def test_hidden_last_name_only_shown_to_admin(self, api_client, manage_events_headers, club):
        rep = make_user(first_name="sam", last_name="secret", hide_last_name=True)
        club.reps.set([rep])

        response = _put(api_client, manage_events_headers, club, [rep.id])
        assert response.json()["reps"][0]["full_name"] == "sam"

        admin = make_user(PermissionKey.MANAGE_EVENTS)
        admin.roles.add(Role.objects.get_or_create(name="admin", defaults={"is_default": True})[0])
        response = _put(api_client, auth_headers_for(admin), club, [rep.id])
        assert response.json()["reps"][0]["full_name"] == "sam secret"
