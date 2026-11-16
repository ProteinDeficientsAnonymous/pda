import uuid
from datetime import date
from decimal import Decimal

import pytest
from community.models import ReserveEntry
from users.permissions import PermissionKey

from tests._mcp_tool_helpers import run_tool, tool_error, tool_names
from tests._users import make_user

TOOLS = {"list_reserve_entries", "save_reserve_entry", "delete_reserve_entry"}


@pytest.fixture
def editor(db):
    return make_user(PermissionKey.EDIT_GUIDELINES)


@pytest.fixture
def entry(db):
    return ReserveEntry.objects.create(
        label="peacefood walk", occurred_on=date(2026, 9, 12), collected=Decimal("315.00")
    )


@pytest.mark.django_db
class TestReserveTools:
    def test_need_edit_guidelines(self, editor):
        assert not TOOLS & tool_names(make_user())
        assert TOOLS <= tool_names(editor)

    def test_list(self, editor, entry):
        result = run_tool(editor, "list_reserve_entries")

        assert [e["label"] for e in result["entries"]] == ["peacefood walk"]

    def test_save_creates(self, editor):
        result = run_tool(
            editor,
            "save_reserve_entry",
            fields={"label": "stickers", "occurred_on": "2026-11-15", "paid_out": "103.65"},
        )

        assert result["left_over"] == "-103.65"
        assert ReserveEntry.objects.get().paid_out == Decimal("103.65")

    def test_save_new_needs_label_and_date(self, editor):
        assert "needs a label and occurred_on" in tool_error(
            editor, "save_reserve_entry", fields={"paid_out": "1"}
        )

    def test_save_updates_only_given_fields(self, editor, entry):
        run_tool(
            editor, "save_reserve_entry", entry_id=str(entry.id), fields={"paid_out": "288.68"}
        )

        entry.refresh_from_db()
        assert entry.paid_out == Decimal("288.68")
        assert entry.collected == Decimal("315.00")

    def test_delete_previews_then_deletes(self, editor, entry):
        preview = run_tool(editor, "delete_reserve_entry", entry_id=str(entry.id))
        assert ReserveEntry.objects.exists()

        run_tool(
            editor,
            "delete_reserve_entry",
            entry_id=str(entry.id),
            confirm_token=preview["confirm_token"],
        )

        assert not ReserveEntry.objects.exists()

    def test_delete_unknown_entry(self, editor):
        missing = str(uuid.uuid4())
        assert f"no reserve entry with id {missing}" in tool_error(
            editor, "delete_reserve_entry", entry_id=missing
        )
