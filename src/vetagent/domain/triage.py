"""'Should I come in?' routing (docs/requirements.md TR-1 to TR-4).

Routes a worried owner to one of three actions. It never names a condition. The symptom list
and thresholds are demo content: each clinic's vets review and approve their own.
"""

from dataclasses import dataclass
from enum import StrEnum


class Level(StrEnum):
    CALL_NOW = "call_now"
    WITHIN_24H = "within_24h"
    WATCH = "watch"


@dataclass(frozen=True)
class Symptom:
    key: str
    label: str
    red_flag: bool = False
    amber_after_hours: int | None = None  # None: duration alone never makes it amber


SYMPTOMS: tuple[Symptom, ...] = (
    # Red flags: always call now (keep in step with agent/safety.py, AG-3).
    Symptom("breathing", "Breathing fast, noisy or with effort", red_flag=True),
    Symptom("collapse", "Collapsed, or can't stand", red_flag=True),
    Symptom("seizure", "Seizure or fitting", red_flag=True),
    Symptom("bleeding", "Bleeding that won't stop", red_flag=True),
    Symptom("bloat", "Swollen tight belly, or retching with nothing coming up", red_flag=True),
    Symptom("urine", "Straining to pee with little or nothing coming out", red_flag=True),
    Symptom("poison", "Ate something that might be poisonous", red_flag=True),
    Symptom("trauma", "Hit by a car or a bad fall", red_flag=True),
    Symptom("leg_up", "Holding a leg up, won't put weight on it", red_flag=True),
    Symptom("tick", "Wobbly back legs or a changed bark or meow (paralysis tick)", red_flag=True),
    Symptom("heat", "Overheated: heavy panting after heat or exercise", red_flag=True),
    Symptom("eye_injury", "Eye injury, or an eye suddenly cloudy", red_flag=True),
    # Everything else depends on how long, and how the pet is otherwise.
    Symptom("vomiting", "Vomiting", amber_after_hours=24),
    Symptom("diarrhoea", "Diarrhoea", amber_after_hours=24),
    Symptom("not_eating", "Not eating", amber_after_hours=24),
    Symptom("limping", "Limping, but still using the leg", amber_after_hours=48),
    Symptom("coughing", "Coughing", amber_after_hours=72),
    Symptom("eye", "Watery or squinting eye", amber_after_hours=0),
    Symptom("ear", "Shaking head or scratching an ear", amber_after_hours=48),
    Symptom("thirst", "Drinking or peeing much more than usual", amber_after_hours=0),
    Symptom("low_energy", "Quiet, low energy", amber_after_hours=24),
    Symptom("skin", "Itchy, scratching or chewing skin"),
    Symptom("lump", "Found a new lump"),
)
BY_KEY = {s.key: s for s in SYMPTOMS}
DURATIONS: tuple[tuple[int, str], ...] = (
    (3, "Under 6 hours"),
    (12, "6 to 24 hours"),
    (48, "1 to 3 days"),
    (96, "More than 3 days"),
)
SPECIES = ("dog", "cat")  # TR-4: the rules were written for dogs and cats only


@dataclass(frozen=True)
class Route:
    level: Level
    headline: str
    advice: str


def route(symptom_key: str, hours: int, eating_normally: bool, bright: bool) -> Route:
    """TR-1, TR-2: red flags call now; otherwise duration and how the pet is decide."""
    symptom = BY_KEY.get(symptom_key)
    if symptom is None:
        raise ValueError(f"Unknown symptom: {symptom_key}")
    if hours not in {h for h, _ in DURATIONS}:
        raise ValueError(f"Unknown duration: {hours}")
    if symptom.red_flag or (not bright and not eating_normally):
        return Route(
            Level.CALL_NOW,
            "Call now",
            "This shouldn't wait. Call the clinic now. If it's closed, call the emergency "
            "vet below and tell them what you're seeing.",
        )
    lasting = symptom.amber_after_hours is not None and hours >= symptom.amber_after_hours
    if lasting or not bright or not eating_normally:
        return Route(
            Level.WITHIN_24H,
            "See a vet within 24 hours",
            "Book the first appointment you can. If it gets worse before then, call.",
        )
    return Route(
        Level.WATCH,
        "Keep an eye on it",
        "Watch for changes over the next day. You can send the vet a note for the morning. "
        "If anything gets worse, or you're worried, call. You know your pet best.",
    )
