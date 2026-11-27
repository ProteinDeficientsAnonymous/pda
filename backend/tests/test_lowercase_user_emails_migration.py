import importlib

import pytest
from django.apps import apps
from users.models import User

migration = importlib.import_module("users.migrations.0065_lowercase_user_emails_ci_unique")


@pytest.mark.django_db
def test_forwards_lowercases_and_strips_existing_emails():
    mixed = User.objects.create_user(phone_number="+12025550101", first_name="a", email="x@x.org")
    clean = User.objects.create_user(phone_number="+12025550102", first_name="b", email="b@x.org")
    User.objects.filter(pk=mixed.pk).update(email=" Foo@X.org ")

    migration.lowercase_emails(apps, None)

    mixed.refresh_from_db()
    clean.refresh_from_db()
    assert mixed.email == "foo@x.org"
    assert clean.email == "b@x.org"
