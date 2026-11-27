"""Club model — the admin-managed list of pda clubs."""

import uuid

from django.db import models

CLUB_NAME_MAX = 80
CLUB_REQUIREMENTS_MAX = 200


class Club(models.Model):
    """A pda club (e.g. "book club"). Club events and join-form club interests point here."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=CLUB_NAME_MAX, unique=True)
    # Who can join, shown next to the name on the join form, e.g. "must be dog parent // guardian".
    requirements = models.CharField(max_length=CLUB_REQUIREMENTS_MAX, blank=True, default="")
    reps = models.ManyToManyField("users.User", blank=True, related_name="rep_clubs")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "community"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
