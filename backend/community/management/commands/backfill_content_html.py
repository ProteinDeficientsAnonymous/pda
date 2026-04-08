"""Backfill content_html fields from existing Delta JSON content."""

from django.core.management.base import BaseCommand

from community._delta_html import delta_to_html
from community.models import FAQ, CommunityGuidelines, EditablePage, HomePage
from community.models.document import Document


class Command(BaseCommand):
    help = "Convert existing Delta JSON content to HTML and store in content_html fields."

    def handle(self, *args, **options):
        self._backfill_singleton(CommunityGuidelines, "CommunityGuidelines")
        self._backfill_singleton(FAQ, "FAQ")
        self._backfill_homepage()
        self._backfill_queryset(EditablePage.objects.all(), "EditablePage", fields=["content"])
        self._backfill_queryset(Document.objects.all(), "Document", fields=["content"])

    def _backfill_singleton(self, model_cls, label: str) -> None:
        obj = model_cls.get()
        if obj.content and not obj.content_html:
            obj.content_html = delta_to_html(obj.content)
            obj.save(update_fields=["content_html"])
            self.stdout.write(f"{label}: converted")
        else:
            self.stdout.write(f"{label}: skipped (empty or already converted)")

    def _backfill_homepage(self) -> None:
        h = HomePage.get()
        changed = []
        if h.content and not h.content_html:
            h.content_html = delta_to_html(h.content)
            changed.append("content_html")
        if h.join_content and not h.join_content_html:
            h.join_content_html = delta_to_html(h.join_content)
            changed.append("join_content_html")
        if changed:
            h.save(update_fields=changed)
            self.stdout.write(f"HomePage: converted {changed}")
        else:
            self.stdout.write("HomePage: skipped (empty or already converted)")

    def _backfill_queryset(self, qs, label: str, fields: list[str]) -> None:
        count = 0
        for obj in qs:
            changed = []
            for field in fields:
                html_field = f"{field}_html"
                value = getattr(obj, field, "")
                current_html = getattr(obj, html_field, "")
                if value and not current_html:
                    setattr(obj, html_field, delta_to_html(value))
                    changed.append(html_field)
            if changed:
                obj.save(update_fields=changed)
                count += 1
        self.stdout.write(f"{label}: converted {count} record(s)")
