import importlib

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone

migration = importlib.import_module("users.migrations.0072_move_pause_flag_to_status")
BEFORE = [("users", "0071_user_status_before_archive")]


@pytest.fixture
def historical_apps(transactional_db):
    executor = MigrationExecutor(connection)
    executor.migrate(BEFORE)
    yield executor.loader.project_state(BEFORE).apps
    executor.loader.build_graph()
    executor.migrate(executor.loader.graph.leaf_nodes())


def test_paused_flag_moves_onto_the_status(historical_apps):
    User = historical_apps.get_model("users", "User")

    def make(phone, **fields):
        return User.objects.create(phone_number=phone, **fields)

    tentative = make(
        "+12025550601",
        membership_status="tentative",
        is_paused=True,
        attendance_paused_at=timezone.now(),
    )
    none = make("+12025550602", membership_status="none", is_paused=True)
    archived = make(
        "+12025550603",
        membership_status="archived",
        is_paused=True,
        status_before_archive="attendance_paused",
    )
    active = make("+12025550604", membership_status="active_member")

    migration.move_pause_flag_to_status(historical_apps, None)

    for user in (tentative, none, archived, active):
        user.refresh_from_db()
    assert tentative.membership_status == none.membership_status == "guidelines_paused"
    assert tentative.attendance_paused_at is None
    assert archived.membership_status == "archived"
    assert archived.status_before_archive == "guidelines_paused"
    assert active.membership_status == "active_member"
