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
