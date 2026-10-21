import io
import secrets
from dataclasses import dataclass

from django.core.files.base import ContentFile
from PIL import Image

from community.models import RsvpQuestionType

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


@dataclass(frozen=True)
class QuestionTemplate:
    label: str
    field_type: str
    options: tuple[str, ...] = ()
    sample_answers: tuple[str, ...] = ()


_QUESTION_TEMPLATES = [
    QuestionTemplate(
        "how are you getting there?",
        RsvpQuestionType.SELECT,
        options=("driving", "transit", "bike", "walking"),
    ),
    QuestionTemplate(
        "any dietary needs?",
        RsvpQuestionType.CHECKBOX,
        options=("gluten-free", "nut-free", "soy-free", "no onion or garlic"),
    ),
    QuestionTemplate(
        "what are you bringing?",
        RsvpQuestionType.TEXTAREA,
        sample_answers=("lentil soup", "cashew mac and cheese", "a big green salad", "cookies"),
    ),
    QuestionTemplate(
        "how did you hear about this?",
        RsvpQuestionType.SELECT,
        options=("a friend", "instagram", "the calendar", "a flyer"),
    ),
    QuestionTemplate(
        "which activities interest you?",
        RsvpQuestionType.CHECKBOX,
        options=("cooking demo", "panel", "potluck", "games"),
    ),
    QuestionTemplate(
        "anything the hosts should know?",
        RsvpQuestionType.TEXTAREA,
        sample_answers=("running a few minutes late", "first time coming!", "bringing a friend"),
    ),
    QuestionTemplate(
        "can you help with setup or cleanup?",
        RsvpQuestionType.SELECT,
        options=("setup", "cleanup", "both", "neither"),
    ),
    QuestionTemplate(
        "any accessibility needs?",
        RsvpQuestionType.TEXTAREA,
        sample_answers=("step-free entrance please", "need a seat near the front", "none"),
    ),
]


def pick_question_templates(count: int) -> list[QuestionTemplate]:
    """Cycles the template pool, suffixing repeats so labels stay unique per event."""
    picked = []
    for i in range(count):
        template = _QUESTION_TEMPLATES[i % len(_QUESTION_TEMPLATES)]
        cycle = i // len(_QUESTION_TEMPLATES)
        if cycle:
            template = QuestionTemplate(
                f"{template.label} ({cycle + 1})",
                template.field_type,
                template.options,
                template.sample_answers,
            )
        picked.append(template)
    return picked


def random_answer(template: QuestionTemplate) -> str:
    if template.field_type == RsvpQuestionType.TEXTAREA:
        return secrets.choice(template.sample_answers)
    if template.field_type == RsvpQuestionType.SELECT:
        return secrets.choice(template.options)
    chosen = [option for option in template.options if secrets.randbelow(2)]
    return ",".join(chosen or [secrets.choice(template.options)])
