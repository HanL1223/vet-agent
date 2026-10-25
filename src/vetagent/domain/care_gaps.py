"""Care-gap rules (docs/requirements.md CG-1 to CG-6).

Pure functions: given a pet, its events, a price list and today's date, return open gaps.
Each rule returns a `Due` (what is due, when, and how often it repeats); `find_gaps` decides
the status. The 12-month forecast (HT-4) projects the same `Due`s forward.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

from vetagent.domain.models import CareEvent, CareGap, GapStatus, GapType, Pet

DUE_SOON_DAYS = 14
SENIOR_AGE = {"dog": 8, "cat": 10}
YEAR = timedelta(days=365)


@dataclass(frozen=True)
class Due:
    type: GapType
    title: str
    reason: str
    due_date: date
    value: int
    every_days: int | None = None  # None: happens once


def upcoming_care(pet: Pet, events: Iterable[CareEvent], prices: dict[str, int]) -> list[Due]:
    """Everything the rules say is due next for this pet, whatever the date."""
    history = sorted((e for e in events if e.pet_id == pet.id), key=lambda e: e.date)
    dues = [
        _vaccination(history, prices),
        *_parasites(history, prices),
        _senior_screening(pet, history, prices),
        _dental(history, prices),
    ]
    return [d for d in dues if d]


def find_gaps(
    pet: Pet, events: Iterable[CareEvent], prices: dict[str, int], today: date
) -> list[CareGap]:
    gaps = []
    for due in upcoming_care(pet, events, prices):
        status = _status(due.due_date, today)
        if status:
            gaps.append(
                CareGap(
                    pet_id=pet.id,
                    type=due.type,
                    title=due.title,
                    reason=due.reason,
                    due_date=due.due_date,
                    status=status,
                    value=due.value,
                )
            )
    return gaps


def life_stage(pet: Pet, today: date) -> str:
    """Young under 1, senior from the CG-3 senior age, adult in between."""
    age = pet.age_on(today)
    if age < 1:
        return "young"
    senior_age = SENIOR_AGE.get(pet.species)
    return "senior" if senior_age is not None and age >= senior_age else "adult"


def rank_by_value(gaps: Iterable[CareGap]) -> list[CareGap]:
    return sorted(gaps, key=lambda g: (-g.value, g.due_date))


def short_date(day: date) -> str:
    return f"{day.day} {day:%b %Y}"


def due_label(gap: CareGap, today: date) -> str:
    days = gap.days_from(today)
    if gap.status is GapStatus.OVERDUE:
        return f"{-days} day{'s' if days != -1 else ''} overdue"
    if days == 0:
        return "Due today"
    return f"Due in {days} day{'s' if days != 1 else ''}"


def _status(due: date, today: date) -> GapStatus | None:
    """CG-5."""
    if due < today:
        return GapStatus.OVERDUE
    if due <= today + timedelta(days=DUE_SOON_DAYS):
        return GapStatus.DUE_SOON
    return None


def _add_years(day: date, years: int) -> date:
    try:
        return day.replace(year=day.year + years)
    except ValueError:  # 29 Feb in a non-leap year
        return day.replace(year=day.year + years, day=28)


def _last(history: list[CareEvent], type_: str) -> CareEvent | None:
    matches = [e for e in history if e.type == type_]
    return matches[-1] if matches else None


def _vaccination(history: list[CareEvent], prices: dict[str, int]) -> Due | None:
    """CG-1: annual booster; no history means no gap."""
    last = _last(history, "vaccination")
    if last is None:
        return None
    vaccine = last.detail.split(" ")[0]
    return Due(
        type=GapType.VACCINATION,
        title=f"{vaccine} vaccine booster",
        reason=f"Last {vaccine} on {short_date(last.date)} · annual schedule",
        due_date=last.date + YEAR,
        value=prices["vaccination"],
        every_days=YEAR.days,
    )


def _parasites(history: list[CareEvent], prices: dict[str, int]) -> list[Due]:
    """CG-2: each product repeats `repeat_days` after its latest dispense."""
    latest: dict[str, CareEvent] = {}
    for e in history:
        if e.type == "parasite" and e.repeat_days:
            latest[e.detail] = e
    return [
        Due(
            type=GapType.PARASITE,
            title=f"{e.detail} due",
            reason=f"Last dispensed {short_date(e.date)} · repeats every {e.repeat_days} days",
            due_date=e.date + timedelta(days=e.repeat_days),
            value=prices[e.price_key or "parasite_repeat"],
            every_days=e.repeat_days,
        )
        for e in latest.values()
    ]


def _senior_screening(pet: Pet, history: list[CareEvent], prices: dict[str, int]) -> Due | None:
    """CG-3: yearly screening from the senior birthday."""
    senior_age = SENIOR_AGE.get(pet.species)
    if senior_age is None:
        return None
    senior_from = _add_years(pet.birth_date, senior_age)
    last = _last(history, "screening")
    if last:
        due = max(last.date + YEAR, senior_from)
        reason = f"Last screening {last.date:%b %Y} · every 12 months for seniors"
    else:
        due = senior_from
        reason = f"Turns {senior_age} on {short_date(senior_from)} · starts senior care"
    return Due(
        type=GapType.SENIOR,
        title="Senior health screening",
        reason=reason,
        due_date=due,
        value=prices["senior_screening"],
        every_days=YEAR.days,
    )


def _dental(history: list[CareEvent], prices: dict[str, int]) -> Due | None:
    """CG-4: a dental finding with no later dental procedure."""
    finding = next((e for e in reversed(history) if e.finding == "dental_recommended"), None)
    if finding is None:
        return None
    if any(e.type == "dental" and e.date >= finding.date for e in history):
        return None
    return Due(
        type=GapType.DENTAL,
        title="Dental scale and polish",
        reason=f"{finding.detail} on {short_date(finding.date)} · not yet booked",
        due_date=finding.date,
        value=prices["dental"],
    )
