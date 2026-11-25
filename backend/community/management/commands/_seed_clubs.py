from community.models import Club

# (name, requirements to join)
SEED_CLUBS = [
    ("doggie meetup club", "must be dog parent // guardian"),
    ("queer and vegan", "must identify as queer // 2slgbtqia+"),
    ("board game club", ""),
    ("movie club", ""),
    ("book club", ""),
    ("outdoor adventures", ""),
]


def seed_clubs(stdout) -> None:
    for name, requirements in SEED_CLUBS:
        _, created = Club.objects.get_or_create(name=name, defaults={"requirements": requirements})
        stdout.write(f"  Club '{name}': {'Created' if created else 'Already exists'}")
