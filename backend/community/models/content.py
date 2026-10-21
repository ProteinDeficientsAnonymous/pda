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
    after approving a join request. Placeholders ${FIRST_NAME}, ${SENDER_NAME},
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


class TentativeApprovalMessageTemplate(models.Model):
    """Singleton — only one row ever exists (pk=1).

    Plain-text body for the sms/whatsapp message a vetter sends right after
    tentatively approving a join request. Placeholders ${FIRST_NAME},
    ${SENDER_NAME}, ${WHATSAPP_LINK}, ${MAGIC_LINK} are substituted client-side
    when rendered.
    """

    body = models.TextField(default="", max_length=4000)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "community"
        verbose_name = "Tentative Approval Message Template"
        verbose_name_plural = "Tentative Approval Message Template"

    def __str__(self) -> str:
        return "Tentative Approval Message Template"

    @classmethod
    def get(cls) -> "TentativeApprovalMessageTemplate":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class MemberPromotionMessageTemplate(models.Model):
    """Singleton — only one row ever exists (pk=1).

    Plain-text body for the sms/whatsapp message a vetter sends after manually
    promoting a tentatively-approved applicant to full member. Placeholders
    ${FIRST_NAME}, ${SENDER_NAME}, ${WHATSAPP_LINK}, ${MAGIC_LINK} are
    substituted client-side when rendered.
    """

    body = models.TextField(default="", max_length=4000)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "community"
        verbose_name = "Member Promotion Message Template"
        verbose_name_plural = "Member Promotion Message Template"

    def __str__(self) -> str:
        return "Member Promotion Message Template"

    @classmethod
    def get(cls) -> "MemberPromotionMessageTemplate":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class MemberPromotionEmailTemplate(models.Model):
    """Singleton — only one row ever exists (pk=1).

    Plain-text body for the email sent automatically when a tentatively-
    approved applicant is promoted to full member (manually or via in-person
    event check-in). Placeholder ${FIRST_NAME} is substituted server-side when
    rendered — there is no sender, this is not a vetter-composed message.
    """

    body = models.TextField(default="", max_length=4000)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "community"
        verbose_name = "Member Promotion Email Template"
        verbose_name_plural = "Member Promotion Email Template"

    def __str__(self) -> str:
        return "Member Promotion Email Template"

    @classmethod
    def get(cls) -> "MemberPromotionEmailTemplate":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class RejectionEmailTemplate(models.Model):
    """Singleton — only one row ever exists (pk=1).

    Body of the email sent automatically when a join request is rejected, plus
    the email text for each preset rejection reason. ${FIRST_NAME} and
    ${REASON} are substituted server-side; ${REASON} is blank when none is given.
    """

    body = models.TextField(
        default=(
            "thank you so much for your interest in pda. after reviewing your request, "
            "we aren't able to welcome you into the community right now.\n\n"
            "${REASON}"
        ),
        max_length=4000,
    )
    vegetarian_text = models.TextField(
        default=(
            "pda is a community for vegans, and from your answers it sounds like you're "
            "vegetarian right now. you're welcome to apply again once you're vegan 🌱"
        ),
        max_length=1000,
    )
    not_vegan_text = models.TextField(
        default=(
            "pda is a community for vegans, and from your answers it sounds like you "
            "aren't vegan right now. you're welcome to apply again once you are 🌱"
        ),
        max_length=1000,
    )
    questions_not_answered_text = models.TextField(
        default=(
            "some of the questions on the join form weren't answered, so we couldn't "
            "review your request. you're welcome to apply again with full answers."
        ),
        max_length=1000,
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "community"
        verbose_name = "Rejection Email Template"
        verbose_name_plural = "Rejection Email Template"

    def __str__(self) -> str:
        return "Rejection Email Template"

    @classmethod
    def get(cls) -> "RejectionEmailTemplate":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class WhatsAppLinkConfig(models.Model):
    """Singleton — only one row ever exists (pk=1).

    Admin-editable WhatsApp group/community invite link, substituted into the
    welcome and tentative-approval message templates via ${WHATSAPP_LINK}.
    """

    link = models.CharField(default="", max_length=200)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "community"
        verbose_name = "WhatsApp Link"
        verbose_name_plural = "WhatsApp Link"

    def __str__(self) -> str:
        return "WhatsApp Link"

    @classmethod
    def get(cls) -> "WhatsAppLinkConfig":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
