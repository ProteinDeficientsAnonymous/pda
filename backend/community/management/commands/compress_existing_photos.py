import time

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from users.models import User

from community._image_compress import AVATAR_MAX_EDGE, EVENT_MAX_EDGE, compress_photo
from community.models import Event


class Command(BaseCommand):
    help = (
        "Recompress stored event and profile photos into new objects; "
        "originals stay in storage. Dry-run unless --commit."
    )

    def add_arguments(self, parser):
        parser.add_argument("--commit", action="store_true", help="write compressed files")

    def handle(self, *args, **options):
        commit = options["commit"]
        changed = skipped = 0
        for event in Event.objects.exclude(photo="").iterator():
            if self._recompress(
                event, "photo", EVENT_MAX_EDGE, f"{event.id}_{int(time.time())}", commit
            ):
                changed += 1
            else:
                skipped += 1
        for user in User.objects.exclude(profile_photo="").iterator():
            if self._recompress(
                user,
                "profile_photo",
                AVATAR_MAX_EDGE,
                f"{user.pk}_{int(time.time())}",
                commit,
            ):
                changed += 1
            else:
                skipped += 1
        self.stdout.write(f"{'wrote' if commit else 'would write'} {changed}; skipped {skipped}")

    def _recompress(
        self, instance, field_name: str, max_edge: int, stem: str, commit: bool
    ) -> bool:
        field = getattr(instance, field_name)
        try:
            field.open("rb")
            try:
                raw = field.read()
            finally:
                field.close()
            result = compress_photo(raw, max_edge)
        except OSError:
            self.stdout.write(f"skip {field.name}: cannot read")
            return False
        if result is None:
            return False
        data, ext = result
        if not commit:
            self.stdout.write(
                f"keep {field.name}; would write {stem}.{ext} ({len(raw)} → {len(data)})"
            )
            return True
        old_name = field.name
        field.save(f"{stem}.{ext}", ContentFile(data), save=False)
        instance.photo_updated_at = timezone.now()
        instance.save(update_fields=[field_name, "photo_updated_at"])
        self.stdout.write(f"keep {old_name}; now {field.name} ({len(raw)} → {len(data)})")
        return True
