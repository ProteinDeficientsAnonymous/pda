import pytest
from community.models import Event, JoinRequest
from django.core.management import call_command
from users.models import User


@pytest.mark.django_db
def test_seed_creates_expected_data():
    call_command("seed")

    assert User.objects.filter(phone_number="+17025550001").exists()
    assert User.objects.filter(phone_number="+17025550002").exists()
    assert Event.objects.count() == 4
    assert JoinRequest.objects.count() == 8


@pytest.mark.django_db
def test_seed_is_idempotent():
    call_command("seed")
    call_command("seed")

    assert User.objects.filter(phone_number__startswith="+1702555").count() == 5
    assert Event.objects.count() == 4
    assert JoinRequest.objects.count() == 8


@pytest.mark.django_db
def test_seed_admin_has_superuser_privileges():
    call_command("seed")

    admin = User.objects.get(phone_number="+17025550001")
    assert admin.is_superuser
    assert admin.is_staff
    assert admin.roles.filter(name="admin").exists()
