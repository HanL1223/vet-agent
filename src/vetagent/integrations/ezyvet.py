"""ezyVet adapter: maps ezyVet API records to the app's domain models (docs/ezyvet.md).

`EzyVetPracticeSystem` reads through an `EzyVetSource`. The demo uses `FileSource`, which serves
saved list responses from data/ezyvet/ (fictional clinic, real ezyVet shape). A live source with
OAuth, paging and rate limits implements the same `list` method; nothing else changes.

`clinic_config.json` holds what ezyVet does not know: which products price each care type, which
standard-of-care groups are which care type, and what each wellness plan covers.
"""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Protocol
from zoneinfo import ZoneInfo

from vetagent.domain.models import (
    BenefitUse,
    CareEvent,
    Membership,
    Owner,
    ParasiteProduct,
    Pet,
    Plan,
)

DEMO_DIR = Path(__file__).resolve().parent.parent / "data" / "ezyvet"


class EzyVetSource(Protocol):
    def list(self, endpoint: str) -> list[dict[str, Any]]: ...


class FileSource:
    """Saved list responses, one file per endpoint: `v1/animal` -> `v1_animal.json`."""

    def __init__(self, folder: Path = DEMO_DIR) -> None:
        self._folder = folder

    def list(self, endpoint: str) -> list[dict[str, Any]]:
        path = self._folder / f"{endpoint.replace('/', '_')}.json"
        return unwrap(json.loads(path.read_text(encoding="utf-8")))


def unwrap(response: dict[str, Any]) -> list[dict[str, Any]]:
    """ezyVet lists come as {"meta": {...}, "items": [{"animal": {...}}, ...]}."""
    return [next(iter(item.values())) for item in response["items"]]


def load_config(folder: Path = DEMO_DIR) -> dict[str, Any]:
    return json.loads((folder / "clinic_config.json").read_text(encoding="utf-8"))


class EzyVetPracticeSystem:
    """Reads everything once at start-up; the demo data is small and a live source caches too."""

    def __init__(self, source: EzyVetSource | None = None, config: dict | None = None) -> None:
        source = source or FileSource()
        self._config = config or load_config()
        self._tz = ZoneInfo(self._config["timezone"])
        self._read_clinic(source)
        self._read_patients(source)
        self._read_care(source)
        self._read_plans(source)

    # --- PracticeSystem --------------------------------------------------------------

    def clinic_name(self) -> str:
        return self._config["clinic_name"]

    def lead_vet(self) -> str:
        return self._lead_vet

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

    def parasite_products(self) -> list[ParasiteProduct]:
        return [
            ParasiteProduct(g["label"], g["lasts_days"], g.get("owner_given", False))
            for g in self._config["care_groups"].values()
            if g["type"] == "parasite"
        ]

    # --- Reading ---------------------------------------------------------------------

    def _read_clinic(self, source: EzyVetSource) -> None:
        users = {str(u["id"]): u for u in source.list("v1/user")}
        vet = users[self._config["lead_vet_user_id"]]
        self._lead_vet = f"{vet.get('title') or 'Dr'} {vet['last_name']}"
        products = {str(p["id"]): p for p in source.list("v1/product")}
        self._prices = {
            key: round(float(products[product_id]["price"]))
            for key, product_id in self._config["price_products"].items()
        }

    def _read_patients(self, source: EzyVetSource) -> None:
        species = {str(s["id"]): s["name"] for s in source.list("v1/species")}
        breeds = {str(b["id"]): b["name"] for b in source.list("v1/breed")}
        self._owners = {str(c["id"]): to_owner(c) for c in source.list("v1/contact")}
        self._pets = {}
        for animal in source.list("v1/animal"):
            if not is_current_patient(animal):
                continue
            kind = species.get(str(animal["species_id"]), "")
            self._pets[str(animal["id"])] = Pet(
                id=str(animal["id"]),
                name=animal["name"],
                species=self._config["species"].get(kind, kind.lower()),
                breed=breeds.get(str(animal["breed_id"]), ""),
                birth_date=self._date(animal["date_of_birth"]),
                owner_id=str(animal["contact_id"]),
            )

    def _read_care(self, source: EzyVetSource) -> None:
        groups = self._config["care_groups"]
        events: list[CareEvent] = []
        for record in source.list("v2/standardofcare"):
            group = groups.get(record["soc_group"]["name"])
            if group:
                events += self._care_events(record, group)
        for consult in source.list("v1/consult"):
            events.append(
                CareEvent(
                    str(consult["animal_id"]),
                    "consult",
                    self._date(consult["date"]),
                    detail=consult.get("description") or "",
                )
            )
        events += self._dispensed(source.list("v1/invoiceline"))
        for status in source.list("v1/healthstatus"):
            if status.get("weight"):
                events.append(
                    CareEvent(
                        str(status["animal_id"]),
                        "weight",
                        self._date(status["created_at"]),
                        kg=float(status["weight"]),
                    )
                )
        # The latest dispense is often in both standard of care and an invoice line.
        unique = dict.fromkeys(e for e in events if e.pet_id in self._pets)
        self._events = list(unique)

    def _dispensed(self, lines: list[dict]) -> list[CareEvent]:
        """Parasite products on invoice lines: the dispensing history behind cover (HT-5)."""
        by_product = {
            g["product_id"]: g
            for g in self._config["care_groups"].values()
            if g["type"] == "parasite" and g.get("product_id")
        }
        events = []
        for line in lines:
            group = by_product.get(str(line.get("product_id")))
            if group:
                events.append(
                    CareEvent(
                        str(line["animal_id"]),
                        "parasite",
                        self._date(line["created_at"]),
                        detail=group["label"],
                        repeat_days=group["lasts_days"],
                        price_key=group["price_key"],
                    )
                )
        return events

    def _care_events(self, record: dict, group: dict) -> list[CareEvent]:
        """One standard-of-care record -> the events the care-gap rules read."""
        pet_id, name = str(record["animal_id"]), record["soc_group"]["name"]
        done = self._date(record["last_fulfilled_at"]) if record.get("last_fulfilled_at") else None
        due = self._date(record["due_at"]) if record.get("due_at") else None
        if group["type"] == "dental":
            # A due dental with no later procedure is an exam finding (CG-4).
            events = [CareEvent(pet_id, "dental", done, detail=name)] if done else []
            if due and (done is None or due > done):
                events.append(
                    CareEvent(
                        pet_id, "finding", due, detail=group["label"], finding="dental_recommended"
                    )
                )
            return events
        if done is None:
            return []
        if group["type"] == "parasite":
            return [
                CareEvent(
                    pet_id,
                    "parasite",
                    done,
                    detail=group["label"],
                    repeat_days=(due - done).days if due else None,
                    price_key=group["price_key"],
                )
            ]
        return [CareEvent(pet_id, group["type"], done, detail=name)]

    def _read_plans(self, source: EzyVetSource) -> None:
        benefits: dict[str, list[str]] = {}
        for b in source.list("v2/wellnessplanbenefit"):
            benefits.setdefault(str(b["wellness_plan_id"]), []).append(b["name"])
        covers = self._config["plan_covers"]
        self._plans = [
            Plan(
                id=str(p["id"]),
                name=p["name"],
                monthly_price=round(float(p["price"])),
                benefits=benefits.get(str(p["id"]), []),
                covers=covers.get(str(p["id"]), []),
                life_stage=self._config.get("plan_life_stage", {}).get(str(p["id"])),
            )
            for p in source.list("v2/wellnessplan")
            if p.get("active", True)
        ]
        offered = {p.id for p in self._plans}
        active = [
            m
            for m in source.list("v2/wellnessplanmembership")
            if m["status"] == "Active"
            and str(m["animal_id"]) in self._pets
            and str(m["wellness_plan_id"]) in offered  # a retired plan isn't shown or billed
        ]
        self._memberships = [
            Membership(str(m["animal_id"]), str(m["wellness_plan_id"]), self._date(m["start_date"]))
            for m in active
        ]
        member_ids = {str(m["id"]) for m in active}
        self._uses = [
            BenefitUse(
                str(line["animal_id"]),
                self._date(line["created_at"]),
                line["name"],
                round(float(line["total"])),
            )
            for line in source.list("v1/invoiceline")
            if str(line.get("wellness_plan_membership_id")) in member_ids
        ]

    def _date(self, epoch: int | str) -> date:
        """ezyVet timestamps are epoch seconds; the calendar date is the clinic's local one."""
        return datetime.fromtimestamp(int(epoch), self._tz).date()


def to_owner(contact: dict) -> Owner:
    """Show owners as "Priya S.": enough for the clinic list without full surnames."""
    last = (contact.get("last_name") or "").strip()
    name = f"{contact['first_name']} {last[0]}." if last else contact["first_name"]
    return Owner(id=str(contact["id"]), name=name)


def is_current_patient(animal: dict) -> bool:
    """CL-6: deceased or inactive animals never appear and never get reminders."""
    return _yes(animal.get("active", True)) and not _yes(animal.get("is_dead", False))


def _yes(value: Any) -> bool:
    # v1 endpoints return some flags as "1"/"0" strings rather than booleans.
    return value in (True, 1, "1", "true", "True")
