from django.db import models


class SpeechTemplate(models.Model):
    """Singleton model — only one row ever exists (pk=1)."""

    shared_pm = models.TextField(default="", max_length=50000)
    walk_pm = models.TextField(default="", max_length=50000)
    restaurant_pm = models.TextField(default="", max_length=50000)
    open_roles = models.JSONField(default=list)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "community"
        verbose_name = "Speech Template"
        verbose_name_plural = "Speech Template"

    def __str__(self):
        return "Speech Template"

    @classmethod
    def get(cls) -> "SpeechTemplate":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class EventSpeech(models.Model):
    event = models.OneToOneField("community.Event", on_delete=models.CASCADE, related_name="speech")
    values = models.JSONField(default=dict)
    updated_by = models.ForeignKey(
        "users.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "community"

    def __str__(self):
        return f"Speech for {self.event_id}"
