import io
import secrets

from django.core.files.base import ContentFile
from PIL import Image

_TITLE_ADJECTIVES = [
    "cozy",
    "sunny",
    "midnight",
    "backyard",
    "rooftop",
    "seasonal",
    "community",
    "neighborhood",
    "annual",
    "monthly",
]
_TITLE_NOUNS = [
    "potluck",
    "meetup",
    "workshop",
    "movie night",
    "picnic",
    "game night",
    "cooking class",
    "swap meet",
    "book club",
    "hike",
]
_PLACEHOLDER_COLORS = [
    (214, 96, 77),
    (77, 144, 214),
    (96, 176, 110),
    (214, 168, 62),
    (150, 110, 200),
    (60, 170, 170),
]


def random_event_title() -> str:
    adjective = secrets.choice(_TITLE_ADJECTIVES)
    noun = secrets.choice(_TITLE_NOUNS)
    return f"{adjective} {noun}".capitalize()


def generate_placeholder_photo() -> ContentFile:
    """A solid-color 800x600 JPEG so dev test events don't render blank."""
    color = secrets.choice(_PLACEHOLDER_COLORS)
    buffer = io.BytesIO()
    Image.new("RGB", (800, 600), color).save(buffer, format="JPEG")
    return ContentFile(buffer.getvalue(), name=f"{secrets.token_hex(4)}.jpg")
