"""Weekly wellbeing check-ins (docs/requirements.md HT-1 to HT-3).

Owners answer five questions once a week, each scored 0 (worst) to 4 (normal). The questions
are modelled on owner-reported scales such as the Canine Brief Pain Inventory; they track change
over time and never produce a diagnosis.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta

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
LOW_SCORE = 2  # a mobility answer this low is shown as a low week


@dataclass(frozen=True)
class CheckIn:
    week: str  # ISO week, e.g. "2026-W44"
    scores: dict[str, int]

    @property
    def total(self) -> int:
        return sum(self.scores.values())


@dataclass(frozen=True)
class WeekPoint:
    week: str
    total: int | None  # None: no check-in that week
    low: bool  # mobility at or under LOW_SCORE


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
        # bool is a subclass of int; True is not an answer.
        if type(value) is not int or not 0 <= value <= MAX_SCORE:
            raise ValueError(f"{key} must be 0 to {MAX_SCORE}")
    return {key: scores[key] for key in KEYS}


def trend(checkins: Sequence[CheckIn], today: date) -> Trend:
    """HT-2: dropping when the 2 latest weeks are each 2+ points under the 4 weeks before.

    Weeks are calendar weeks, so a gap in check-ins can't make old answers look recent. The
    latest week is this one if the owner has checked in, otherwise last week. Mobility is
    checked first: it is the earliest change owners see in older dogs.
    """
    by_week = {c.week: c for c in checkins}
    latest = today if iso_week(today) in by_week else today - timedelta(weeks=1)
    recent = [by_week.get(iso_week(latest - timedelta(weeks=n))) for n in (1, 0)]
    before = [
        by_week[w]
        for n in range(RECENT_WEEKS, RECENT_WEEKS + BASELINE_WEEKS)
        if (w := iso_week(latest - timedelta(weeks=n))) in by_week
    ]
    if None in recent or len(before) < BASELINE_WEEKS - 1:
        return Trend(dropping=False)
    for measure, value in (
        ("mobility", lambda c: c.scores["mobility"]),
        ("overall", lambda c: c.total),
    ):
        baseline = sum(value(c) for c in before) / len(before)
        values = tuple(value(c) for c in recent)
        if all(v <= baseline - DROP for v in values):
            return Trend(True, measure, round(baseline, 1), values)
    return Trend(dropping=False)


def describe(trend: Trend) -> str | None:
    """Plain words for the owner; no diagnosis."""
    if not trend.dropping:
        return None
    what = "Mobility" if trend.measure == "mobility" else "Overall wellbeing"
    scores = " and ".join(str(v) for v in trend.recent)
    return f"{what} has been lower for 2 weeks ({scores}, usually about {trend.baseline:g})."


def clinic_flag(trend: Trend) -> str | None:
    """HT-3: the short tag on the clinic's list."""
    if not trend.dropping:
        return None
    return f"Home check-ins: {'mobility' if trend.measure == 'mobility' else 'wellbeing'} down"


def recent_weeks(checkins: Sequence[CheckIn], today: date, weeks: int = 8) -> list[WeekPoint]:
    """The last `weeks` calendar weeks up to this one; a missed week has no total."""
    by_week = {c.week: c for c in checkins}
    points = []
    for n in range(weeks - 1, -1, -1):
        week = iso_week(today - timedelta(weeks=n))
        c = by_week.get(week)
        low = c is not None and c.scores["mobility"] <= LOW_SCORE
        points.append(WeekPoint(week, c.total if c else None, low))
    return points
