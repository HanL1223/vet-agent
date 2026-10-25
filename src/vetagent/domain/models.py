"""Domain records shared across the app."""

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum


class GapType(StrEnum):
    VACCINATION = "vaccination"
    PARASITE = "parasite"
    SENIOR = "senior"
    DENTAL = "dental"


class GapStatus(StrEnum):
    OVERDUE = "overdue"
    DUE_SOON = "due_soon"


@dataclass(frozen=True)
class Owner:
    id: str
    name: str


@dataclass(frozen=True)
class Pet:
    id: str
    name: str
    species: str  # "dog" or "cat"
    breed: str
    birth_date: date
    owner_id: str

    def age_on(self, day: date) -> int:
        had_birthday = (day.month, day.day) >= (self.birth_date.month, self.birth_date.day)
        return day.year - self.birth_date.year - (0 if had_birthday else 1)


@dataclass(frozen=True)
class CareEvent:
    pet_id: str
    type: str  # vaccination | screening | parasite | consult | finding | dental | weight
    date: date
    detail: str = ""
    repeat_days: int | None = None
    price_key: str | None = None
    finding: str | None = None
    kg: float | None = None


@dataclass(frozen=True)
class CareGap:
    pet_id: str
    type: GapType
    title: str
    reason: str
    due_date: date
    status: GapStatus
    value: int  # AUD

    def days_from(self, today: date) -> int:
        return (self.due_date - today).days


@dataclass(frozen=True)
class Plan:
    id: str
    name: str
    monthly_price: int
    benefits: list[str] = field(default_factory=list)
    covers: list[str] = field(default_factory=list)  # GapType values included in the plan


@dataclass(frozen=True)
class Membership:
    pet_id: str
    plan_id: str
    start: date


@dataclass(frozen=True)
class BenefitUse:
    pet_id: str
    date: date
    item: str
    value: int


@dataclass(frozen=True)
class ParasiteProduct:
    label: str  # matches CareEvent.detail for parasite events
    lasts_days: int
    owner_given: bool  # a chew or tablet the owner gives at home, not an injection
