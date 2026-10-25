import importlib

import pytest
from django.apps import apps
from users.models import User

pytestmark = pytest.mark.django_db

backfill = importlib.import_module("users.migrations.0053_carry_weekly_digest_opt_out_to_monthly")


def test_carries_weekly_opt_out_to_monthly():
    out = User.objects.create(phone_number="+12025550401", weekly_digest_opt_out=True)
    stays = User.objects.create(phone_number="+12025550402")
    backfill.carry_over_opt_outs(apps, None)
    out.refresh_from_db()
    stays.refresh_from_db()
    assert out.monthly_digest_opt_out is True
    assert stays.monthly_digest_opt_out is False
