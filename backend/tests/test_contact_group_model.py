import pytest
from django.db import IntegrityError
from users.contact_group import ContactGroup
from users.models import User


def _make_user(phone: str) -> User:
    return User.objects.create_user(
        phone_number=phone, password="testpass123", first_name="Test", last_name="Member"
    )


@pytest.mark.django_db
class TestContactGroupModel:
    def test_create_group(self):
        owner = _make_user("+15550002001")
        group = ContactGroup.objects.create(owner=owner, name="board game group")
        assert group.id is not None
        assert group.owner == owner
        assert group.name == "board game group"
        assert group.created_at is not None
        assert group.updated_at is not None
        assert group.members.count() == 0
        assert str(group) == "board game group"

    def test_add_and_remove_members(self):
        owner = _make_user("+15550002002")
        alice = _make_user("+15550002003")
        bob = _make_user("+15550002004")
        group = ContactGroup.objects.create(owner=owner, name="movie club")

        group.members.add(alice, bob)
        assert set(group.members.all()) == {alice, bob}

        group.members.remove(alice)
        assert set(group.members.all()) == {bob}

    def test_owner_reverse_relation(self):
        owner = _make_user("+15550002005")
        ContactGroup.objects.create(owner=owner, name="dinner crew")
        ContactGroup.objects.create(owner=owner, name="walk group")
        assert owner.contact_groups.count() == 2

    def test_membership_reverse_relation(self):
        owner = _make_user("+15550002006")
        member = _make_user("+15550002007")
        group = ContactGroup.objects.create(owner=owner, name="hiking")
        group.members.add(member)
        assert list(member.contact_group_memberships.all()) == [group]

    def test_owner_scoping_isolates_groups(self):
        owner_a = _make_user("+15550002008")
        owner_b = _make_user("+15550002009")
        ContactGroup.objects.create(owner=owner_a, name="a-group")
        ContactGroup.objects.create(owner=owner_b, name="b-group")
        assert list(ContactGroup.objects.filter(owner=owner_a).values_list("name", flat=True)) == [
            "a-group"
        ]

    def test_name_unique_per_owner(self):
        owner = _make_user("+15550002010")
        ContactGroup.objects.create(owner=owner, name="duplicate")
        with pytest.raises(IntegrityError):
            ContactGroup.objects.create(owner=owner, name="duplicate")

    def test_same_name_allowed_for_different_owners(self):
        owner_a = _make_user("+15550002011")
        owner_b = _make_user("+15550002012")
        ContactGroup.objects.create(owner=owner_a, name="shared name")
        ContactGroup.objects.create(owner=owner_b, name="shared name")
        assert ContactGroup.objects.filter(name="shared name").count() == 2

    def test_deleting_owner_cascades(self):
        owner = _make_user("+15550002013")
        ContactGroup.objects.create(owner=owner, name="temp")
        owner.delete()
        assert ContactGroup.objects.count() == 0

    def test_deleting_member_drops_membership_not_group(self):
        owner = _make_user("+15550002014")
        member = _make_user("+15550002015")
        group = ContactGroup.objects.create(owner=owner, name="keep me")
        group.members.add(member)
        member.delete()
        group.refresh_from_db()
        assert ContactGroup.objects.filter(id=group.id).exists()
        assert group.members.count() == 0
