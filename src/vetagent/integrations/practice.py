"""Practice-system port: the read-only clinic records the app depends on.

The app only talks to this interface. `SeedPracticeSystem` serves demo data; a real
ezyVet adapter (OAuth client credentials, 60 calls/min per endpoint) implements the same
methods later without touching the domain, agent or API code.
"""

import json
from datetime import date
from pathlib import Path
from typing import Protocol

from vetagent.domain.models import BenefitUse, CareEvent, Membership, Owner, Pet, Plan

SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "seed_clinic.json"


class PracticeSystem(Protocol):
    def clinic_name(self) -> str: ...
    def lead_vet(self) -> str: ...
    def price_list(self) -> dict[str, int]: ...
    def pets(self) -> list[Pet]: ...
    def pet(self, pet_id: str) -> Pet: ...
    def owner(self, owner_id: str) -> Owner: ...
    def events(self, pet_id: str | None = None) -> list[CareEvent]: ...
    def plans(self) -> list[Plan]: ...
    def memberships(self) -> list[Membership]: ...
    def benefit_uses(self, pet_id: str) -> list[BenefitUse]: ...


class SeedPracticeSystem:
    """Reads demo data in the app's own shape. docs/ezyvet.md maps each field to ezyVet."""

    def __init__(self, path: Path = SEED_PATH) -> None:
        raw = json.loads(path.read_text())
        self._clinic = raw["clinic"]
        self._prices = raw["price_list"]
        self._owners = {o["id"]: Owner(**o) for o in raw["owners"]}
        self._pets = {
            p["id"]: Pet(**{**p, "birth_date": date.fromisoformat(p["birth_date"])})
            for p in raw["pets"]
        }
        self._events = [
            CareEvent(**{**e, "date": date.fromisoformat(e["date"])}) for e in raw["events"]
        ]
        self._plans = [Plan(**p) for p in raw["plans"]]
        self._memberships = [
            Membership(**{**m, "start": date.fromisoformat(m["start"])}) for m in raw["memberships"]
        ]
        self._uses = [
            BenefitUse(**{**u, "date": date.fromisoformat(u["date"])}) for u in raw["benefit_usage"]
        ]

    def clinic_name(self) -> str:
        return self._clinic["name"]

    def lead_vet(self) -> str:
        return self._clinic["lead_vet"]

    def price_list(self) -> dict[str, int]:
        return dict(self._prices)

    def pets(self) -> list[Pet]:
        return list(self._pets.values())

    def pet(self, pet_id: str) -> Pet:
        return self._pets[pet_id]

    def owner(self, owner_id: str) -> Owner:
        return self._owners[owner_id]

    def events(self, pet_id: str | None = None) -> list[CareEvent]:
        return [e for e in self._events if pet_id is None or e.pet_id == pet_id]

    def plans(self) -> list[Plan]:
        return list(self._plans)

    def memberships(self) -> list[Membership]:
        return list(self._memberships)

    def benefit_uses(self, pet_id: str) -> list[BenefitUse]:
        return [u for u in self._uses if u.pet_id == pet_id]
