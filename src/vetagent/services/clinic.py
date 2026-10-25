"""Clinic dashboard use cases (docs/requirements.md CL-1 to CL-5)."""

from dataclasses import dataclass
from datetime import date

from vetagent.domain.care_gaps import due_label, find_gaps, rank_by_value
from vetagent.domain.models import CareGap, GapStatus, GapType
from vetagent.integrations.practice import PracticeSystem
from vetagent.store.sqlite import Store


@dataclass(frozen=True)
class GapRow:
    key: str
    pet: str
    breed: str
    owner: str
    member: bool
    type: str
    title: str
    reason: str
    due_label: str
    overdue: bool
    value: int
    reminded: bool


def gap_key(gap: CareGap) -> str:
    return f"{gap.pet_id}:{gap.type}:{gap.due_date.isoformat()}"


class ClinicService:
    def __init__(self, practice: PracticeSystem, store: Store, today: date) -> None:
        self._practice = practice
        self._store = store
        self._today = today

    def all_gaps(self) -> list[CareGap]:
        prices = self._practice.price_list()
        gaps = [
            gap
            for pet in self._practice.pets()
            for gap in find_gaps(pet, self._practice.events(pet.id), prices, self._today)
        ]
        return rank_by_value(gaps)

    def gap_rows(self, gap_type: str | None = None) -> list[GapRow]:
        """CL-2, CL-3."""
        members = {m.pet_id for m in self._practice.memberships()}
        reminded = self._store.reminded_keys()
        rows = []
        for gap in self.all_gaps():
            if gap_type and gap.type != GapType(gap_type):
                continue
            pet = self._practice.pet(gap.pet_id)
            rows.append(
                GapRow(
                    key=gap_key(gap),
                    pet=pet.name,
                    breed=f"{pet.breed}, {pet.age_on(self._today)} yrs",
                    owner=self._practice.owner(pet.owner_id).name,
                    member=pet.id in members,
                    type=gap.type.value,
                    title=gap.title,
                    reason=gap.reason,
                    due_label=due_label(gap, self._today),
                    overdue=gap.status is GapStatus.OVERDUE,
                    value=gap.value,
                    reminded=gap_key(gap) in reminded,
                )
            )
        return rows

    def summary(self) -> dict:
        """CL-1."""
        plans = {p.id: p for p in self._practice.plans()}
        memberships = self._practice.memberships()
        gaps = self.all_gaps()
        reminded = self._store.reminded_keys()
        return {
            "clinic": self._practice.clinic_name(),
            "today": self._today.isoformat(),
            "plan_members": len(memberships),
            "monthly_plan_revenue": sum(plans[m.plan_id].monthly_price for m in memberships),
            "pets_with_gaps": len({g.pet_id for g in gaps}),
            "active_pets": len(self._practice.pets()),
            "value_at_risk": sum(g.value for g in gaps),
            "reminders_sent": len(reminded & {gap_key(g) for g in gaps}),
        }

    def send_reminders(self, keys: list[str]) -> int:
        """CL-4. Delivery (SMS/email) is out of scope for the demo; we record the send."""
        valid = {gap_key(g) for g in self.all_gaps()}
        sent = [k for k in keys if k in valid]
        for key in sent:
            self._store.mark_reminded(key)
        return len(sent)

    def plans(self) -> list[dict]:
        """CL-5."""
        counts: dict[str, int] = {}
        for m in self._practice.memberships():
            counts[m.plan_id] = counts.get(m.plan_id, 0) + 1
        return [
            {
                "id": p.id,
                "name": p.name,
                "monthly_price": p.monthly_price,
                "benefits": p.benefits,
                "members": counts.get(p.id, 0),
            }
            for p in self._practice.plans()
        ]

    def clinic_requests(self) -> list[dict]:
        names = {p.id: p.name for p in self._practice.pets()}
        return [
            {**r, "pet": names.get(r["pet_id"], r["pet_id"])} for r in self._store.clinic_requests()
        ]
