"""Clinic estimates shown to owners in plain language (docs/requirements.md CO-1, CO-2).

The clinic writes the estimate; this module only prices it from the owner's side: what is
recommended, what is optional, what their plan includes, and what they would pay. It never
judges whether a line is clinically needed.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from vetagent.domain.models import Plan


@dataclass(frozen=True)
class EstimateLine:
    name: str
    explanation: str  # the clinic's own words for owners; empty when it has none
    low: int
    high: int
    optional: bool
    care_type: str | None  # GapType value the line counts as, for plan inclusion


@dataclass(frozen=True)
class Estimate:
    id: str
    pet_id: str
    title: str
    vet: str
    created: date
    expires: date
    lines: list[EstimateLine]


@dataclass(frozen=True)
class Range:
    low: int
    high: int


@dataclass(frozen=True)
class OwnerPrice:
    recommended: Range  # what the owner pays for recommended lines, after the plan
    with_optional: Range  # the same, plus every optional line
    included: int  # list price the plan includes
    included_lines: frozenset[str]


def owner_price(estimate: Estimate, plan: Plan | None) -> OwnerPrice:
    """CO-2: lines the plan includes cost the owner nothing; everything else is a range."""
    covers = set(plan.covers) if plan else set()
    included = [line for line in estimate.lines if line.care_type in covers]
    payable = [line for line in estimate.lines if line not in included]
    must = [line for line in payable if not line.optional]
    return OwnerPrice(
        recommended=_sum(must),
        with_optional=_sum(payable),
        included=sum(line.high for line in included),
        included_lines=frozenset(line.name for line in included),
    )


def open_estimates(estimates: Iterable[Estimate], today: date) -> list[Estimate]:
    """Newest first; an expired estimate is no longer a price the clinic stands behind."""
    current = [e for e in estimates if e.expires >= today]
    return sorted(current, key=lambda e: e.created, reverse=True)


def _sum(lines: list[EstimateLine]) -> Range:
    return Range(sum(line.low for line in lines), sum(line.high for line in lines))
