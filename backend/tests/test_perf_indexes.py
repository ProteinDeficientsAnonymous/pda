import pytest
from community.models import Event, EventRSVP, JoinRequest
from django.db import connection


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("model", "name", "columns"),
    [
        (Event, "event_status_start_idx", ["status", "start_datetime"]),
        (EventRSVP, "eventrsvp_event_status_idx", ["event_id", "status"]),
        (JoinRequest, "joinrequest_phone_status_idx", ["phone_number", "status"]),
    ],
)
def test_index_exists(model, name, columns):
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(cursor, model._meta.db_table)
    assert constraints[name]["index"]
    assert constraints[name]["columns"] == columns
