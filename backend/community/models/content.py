"""Content models: EditablePage, HomePage, CommunityGuidelines, FAQ, WhatsAppConfig."""

from django.db import models

from community.models.choices import PageVisibility


class CommunityGuidelines(models.Model):
    """Singleton model — only one row ever exists (pk=1)."""

    # Legacy Quill Delta JSON (written by the Flutter client).
    content = models.TextField(default="", max_length=50000)
    # ProseMirror JSON (written by the React/TipTap client). Either field may
    # be empty for any given row; content_html is the canonical read source.
    content_pm = models.TextField(default="", max_length=50000)
    content_html = models.TextField(default="", max_length=100000)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "community"
        verbose_name = "Community Guidelines"
        verbose_name_plural = "Community Guidelines"

    def __str__(self):
        return "Community Guidelines"

    @classmethod
    def get(cls) -> "CommunityGuidelines":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class FAQ(models.Model):
    """Singleton model — only one row ever exists (pk=1)."""

    content = models.TextField(default="", max_length=50000)
    content_pm = models.TextField(default="", max_length=50000)
    content_html = models.TextField(default="", max_length=100000)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "community"
        verbose_name = "FAQ"
        verbose_name_plural = "FAQ"

    def __str__(self):
        return "FAQ"

    @classmethod
    def get(cls) -> "FAQ":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class HomePage(models.Model):
    """Singleton model — only one row ever exists (pk=1)."""

    content = models.TextField(default="", max_length=50000)
    content_pm = models.TextField(default="", max_length=50000)
    content_html = models.TextField(default="", max_length=100000)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "community"
        verbose_name = "Home Page"
        verbose_name_plural = "Home Page"

    def __str__(self):
        return "Home Page"

    @classmethod
    def get(cls) -> "HomePage":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class EditablePage(models.Model):
    """Content pages editable by admins. One row per slug."""

    slug = models.SlugField(max_length=100, unique=True)
    content = models.TextField(default="", max_length=50000)
    content_pm = models.TextField(default="", max_length=50000)
    content_html = models.TextField(default="", max_length=100000)
    visibility = models.CharField(
        max_length=20,
        choices=PageVisibility.choices,
        default=PageVisibility.PUBLIC,
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "community"
        ordering = ["slug"]

    def __str__(self) -> str:
        return f"EditablePage({self.slug})"

    @classmethod
    def get_or_create_page(
        cls, slug: str, default_visibility: str = PageVisibility.PUBLIC
    ) -> "EditablePage":
        obj, _ = cls.objects.get_or_create(
            slug=slug,
            defaults={"visibility": default_visibility},
        )
        return obj


class WelcomeMessageTemplate(models.Model):
    """Singleton — only one row ever exists (pk=1).

    Plain-text template for the welcome SMS/WhatsApp message vetters send
    after approving a join request. Placeholders ${NAME}, ${SENDER_NAME},
    ${MAGIC_LINK} are substituted client-side at render time.
    """

    body = models.TextField(default="", max_length=4000)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "community"
        verbose_name = "Welcome Message Template"
        verbose_name_plural = "Welcome Message Template"

    def __str__(self) -> str:
        return "Welcome Message Template"

    @classmethod
    def get(cls) -> "WelcomeMessageTemplate":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class WhatsAppConfig(models.Model):
    """Singleton model — only one row ever exists (pk=1).

    Stores WhatsApp bot configuration so admins can update it without redeployment.
    Falls back to Django settings if the DB row has empty values.
    """

    bot_url = models.URLField(blank=True, default="")
    bot_secret = models.CharField(max_length=256, blank=True, default="")
    group_id = models.CharField(max_length=256, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "community"
        verbose_name = "WhatsApp Configuration"
        verbose_name_plural = "WhatsApp Configuration"

    def __str__(self) -> str:
        return "WhatsApp Configuration"

    @classmethod
    def get(cls) -> "WhatsAppConfig":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
