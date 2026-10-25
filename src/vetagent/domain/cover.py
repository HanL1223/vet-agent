"""Preventive cover (docs/requirements.md HT-5, HT-6): days protected by parasite products.

Each dose protects from the day it is given for the product's interval. Cover is the share of
the last 365 days protected by at least one dose, per product.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

WINDOW_DAYS = 365


@dataclass(frozen=True)
class Dose:
    product: str
    given_on: date
    lasts_days: int
    owner_reported: bool = False


@dataclass(frozen=True)
class Cover:
    product: str
    covered_days: int
    days_left: int  # from today; 0 when cover has lapsed
    last_given: date
    owner_reported: bool  # the latest dose came from the owner, not the clinic
    spans: list[tuple[int, int]]  # covered runs as [start, end) day offsets in the window

    @property
    def percent(self) -> int:
        return round(100 * self.covered_days / WINDOW_DAYS)


def cover(doses: Iterable[Dose], today: date) -> list[Cover]:
    by_product: dict[str, list[Dose]] = {}
    for dose in doses:
        if dose.given_on > today:  # a future-dated dose protects nothing yet
            continue
        by_product.setdefault(dose.product, []).append(dose)
    return [_cover(product, ds, today) for product, ds in sorted(by_product.items())]


def _cover(product: str, doses: list[Dose], today: date) -> Cover:
    start = today - timedelta(days=WINDOW_DAYS)
    covered = set()
    for d in doses:
        first = max(d.given_on, start)
        last = min(d.given_on + timedelta(days=d.lasts_days), today)
        covered.update(range((first - start).days, (last - start).days))
    ends = [d.given_on + timedelta(days=d.lasts_days) for d in doses]
    latest = max(doses, key=lambda d: (d.given_on, not d.owner_reported))
    return Cover(
        product=product,
        covered_days=len(covered),
        days_left=max([(end - today).days for end in ends] + [0]),
        last_given=latest.given_on,
        owner_reported=latest.owner_reported,
        spans=_runs(sorted(covered)),
    )


def _runs(days: list[int]) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    for day in days:
        if runs and runs[-1][1] == day:
            runs[-1] = (runs[-1][0], day + 1)
        else:
            runs.append((day, day + 1))
    return runs
