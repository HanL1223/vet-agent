"""Weekly wellbeing check-ins (docs/requirements.md HT-1 to HT-3).

Owners answer five questions once a week, each scored 0 (worst) to 4 (normal). The questions
are modelled on owner-reported scales such as the Canine Brief Pain Inventory; they track change
over time and never produce a diagnosis.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

QUESTIONS: tuple[tuple[str, str, str, str], ...] = (
    # key, question, label for 0, label for 4
    ("appetite", "Eating and drinking", "Barely", "Normal"),
    ("energy", "Energy and interest", "Very flat", "Normal"),
    ("mobility", "Getting up, walking, stairs", "Struggling", "Easy"),
    ("comfort", "Comfort at rest", "Restless or sore", "Settled"),
    ("toileting", "Toileting", "Problems", "Normal"),
)
KEYS = tuple(q[0] for q in QUESTIONS)
MAX_SCORE = 4
BASELINE_WEEKS = 4
RECENT_WEEKS = 2
DROP = 2  # points below baseline that count as a real change, not noise


@dataclass(frozen=True)
class CheckIn:
    week: str  # ISO week, e.g. "2026-W44"
    scores: dict[str, int]

    @property
    def total(self) -> int:
        return sum(self.scores.values())


@dataclass(frozen=True)
class Trend:
    dropping: bool
    measure: str | None = None  # "mobility" or "overall"
    baseline: float | None = None
    recent: tuple[int, ...] = ()


def iso_week(day: date) -> str:
    year, week, _ = day.isocalendar()
    return f"{year}-W{week:02d}"


def validate(scores: dict[str, int]) -> dict[str, int]:
    """HT-1: all five answers, each a whole number from 0 to 4."""
    if set(scores) != set(KEYS):
        raise ValueError(f"Answer all of: {', '.join(KEYS)}")
    for key, value in scores.items():
        if not isinstance(value, int) or not 0 <= value <= MAX_SCORE:
            raise ValueError(f"{key} must be 0 to {MAX_SCORE}")
    return {key: scores[key] for key in KEYS}


def trend(checkins: Sequence[CheckIn]) -> Trend:
    """HT-2: dropping when the last 2 check-ins are each 2+ points under the 4 before them.

    Mobility is checked first because it is the earliest sign owners can see in older dogs.
    """
    ordered = sorted(checkins, key=lambda c: c.week)
    if len(ordered) < BASELINE_WEEKS + RECENT_WEEKS:
        return Trend(dropping=False)
    recent = ordered[-RECENT_WEEKS:]
    before = ordered[-(BASELINE_WEEKS + RECENT_WEEKS) : -RECENT_WEEKS]
    for measure, value in (
        ("mobility", lambda c: c.scores["mobility"]),
        ("overall", lambda c: c.total),
    ):
        baseline = sum(value(c) for c in before) / len(before)
        values = tuple(value(c) for c in recent)
        if all(v <= baseline - DROP for v in values):
            return Trend(True, measure, round(baseline, 1), values)
    return Trend(dropping=False)
