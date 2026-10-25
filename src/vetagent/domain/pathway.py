"""First 90 days for a new puppy or kitten (docs/requirements.md NP-1, NP-2).

The vaccine course comes from clinic records; home milestones are ticked by the owner. Timing
follows common Australian practice and is demo content each clinic adjusts.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

from vetagent.domain.models import Pet

YOUNG_DAYS = 183  # NP-1: the pathway shows until about six months old
COURSE_GAP = timedelta(weeks=4)
COURSE_ENDS_WEEKS = 16  # the course runs until a dose at 16 weeks or older


@dataclass(frozen=True)
class Step:
    key: str
    title: str
    detail: str
    done: bool
    when: str = ""  # a date or timing for steps still to do
    owner_ticks: bool = False  # true when the owner marks it done at home
    due: date | None = None  # for course doses still to give


HOME_STEPS = (
    ("microchip", "Microchip and council registration", "Check your council's rules."),
    ("parasites", "Flea, tick and worm prevention started", "Ask which product suits them."),
    ("class", "Puppy class or kitten kindy", "Best before 16 weeks, while they learn fastest."),
)

TIPS = {
    "cat": (
        (10, "One litter tray per cat plus one, away from food and water."),
        (12, "Handle paws, ears and mouth a little every day, so vet visits are easy."),
        (14, "Put a scratching post near where they sleep: cats scratch when they wake."),
        (99, "Play with wand toys, not hands, so biting doesn't become a game."),
    ),
    "dog": (
        (10, "Short, frequent toilet trips: after sleeping, eating and playing."),
        (12, "Handle paws, ears and mouth a little every day, so vet visits are easy."),
        (14, "Meet calm, vaccinated dogs and new people, a few at a time."),
        (99, "Practise short spells alone with a chew toy, so being alone feels normal."),
    ),
}


def is_young(pet: Pet, today: date) -> bool:
    return (today - pet.birth_date).days < YOUNG_DAYS


def weeks_old(pet: Pet, today: date) -> int:
    return (today - pet.birth_date).days // 7


def vaccine_steps(pet: Pet, given: Iterable[date], today: date) -> list[Step]:
    """NP-1: a dose every 4 weeks until one at 16 weeks or older."""
    doses = sorted(d for d in given if d >= pet.birth_date)
    steps = [
        Step(f"vaccine-{i}", f"Vaccination {i}", f"Given {d.day} {d:%b}", True)
        for i, d in enumerate(doses, start=1)
    ]
    course_done = bool(doses) and (doses[-1] - pet.birth_date).days >= COURSE_ENDS_WEEKS * 7
    if course_done:
        return steps
    due = doses[-1] + COURSE_GAP if doses else pet.birth_date + timedelta(weeks=6)
    n = len(doses) + 1
    while True:
        steps.append(
            Step(f"vaccine-{n}", f"Vaccination {n}", "", False, _when(due, today), due=due)
        )
        if (due - pet.birth_date).days >= COURSE_ENDS_WEEKS * 7:
            return steps
        due, n = due + COURSE_GAP, n + 1


def home_steps(pet: Pet, ticked: set[str], today: date) -> list[Step]:
    steps = [
        Step(key, title, detail, key in ticked, owner_ticks=True)
        for key, title, detail in HOME_STEPS
    ]
    desex = pet.birth_date + timedelta(days=150)
    steps.append(
        Step(
            "desexing",
            "Talk to the vet about desexing",
            "Timing depends on breed and size; often around five to six months.",
            "desexing" in ticked,
            f"around {desex:%B}",
            owner_ticks=True,
        )
    )
    return steps


def tip(pet: Pet, today: date) -> str:
    """NP-2: one practical tip for their age this week."""
    age = weeks_old(pet, today)
    tips = TIPS.get(pet.species, TIPS["dog"])
    return next(text for until, text in tips if age < until)


def _when(due: date, today: date) -> str:
    if due < today:
        return "overdue"
    return f"from {due.day} {due:%b}"
