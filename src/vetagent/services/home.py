"""Owner app use cases: one dashboard per pet, built around the moments owners get stuck.

Costs (CO-*), the last visit (VR-*), "Should I come in?" (TR-*), a new pet's first 90 days
(NP-*) and, for senior pets, weekly check-ins (HT-*). Clinic records come from the practice
system; ticks, check-ins, recaps and triage answers are app-owned (PR-3). Nothing here contacts
the clinic: actions become proposals through the owner agent (AG-4).
"""

from datetime import date

from vetagent.domain import checkins as ci
from vetagent.domain import pathway, recaps
from vetagent.domain import triage as tr
from vetagent.domain.care_gaps import (
    Due,
    due_label,
    find_gaps,
    life_stage,
    rank_by_value,
    upcoming_care,
)
from vetagent.domain.estimates import Estimate, open_estimates, owner_price, sent_version
from vetagent.domain.forecast import Forecast, forecast
from vetagent.domain.models import GapType, Pet, Plan
from vetagent.integrations.practice import PracticeSystem
from vetagent.services.local_area import LocalAreaService
from vetagent.store.sqlite import Store


class DashboardError(ValueError):
    pass


class PetNotFound(LookupError):
    pass


class HomeService:
    def __init__(
        self,
        practice: PracticeSystem,
        store: Store,
        today: date,
        owner_id: str,
        local: LocalAreaService | None = None,
    ) -> None:
        self._practice = practice
        self._store = store
        self._today = today
        self._owner_id = owner_id
        self._local = local  # open data about the clinic's area (OD-*); optional

    # Queries -----------------------------------------------------------------
    def pets(self) -> list[dict]:
        """OW-1, BR-1: every current pet this owner registered."""
        return [
            {"id": p.id, "name": p.name, "species": p.species}
            for p in self._practice.pets()
            if p.owner_id == self._owner_id
        ]

    def pet(self, pet_id: str) -> Pet:
        """OW-1: owners only ever see their own pets."""
        try:
            pet = self._practice.pet(pet_id)
        except KeyError:
            pet = None
        if pet is None or pet.owner_id != self._owner_id:
            raise PetNotFound(pet_id)
        return pet

    def dashboard(self, pet_id: str) -> dict:
        pet = self.pet(pet_id)
        stage = life_stage(pet, self._today)
        plan, member, year = self._year_ahead(pet)
        contact = self._practice.contact()
        if self._local:
            contact = self._local.contact(contact)
        return {
            "clinic": self._practice.clinic_name(),
            "contact": {
                "phone": contact.phone,
                "emergency_name": contact.emergency_name,
                "emergency_phone": contact.emergency_phone,
                "emergency_source": contact.emergency_source,
            },
            "pet": {
                "id": pet.id,
                "name": pet.name,
                "species": pet.species,
                "breed": pet.breed,
                "age": pet.age_on(self._today),
                "stage": stage,
                "plan": plan.name if member else None,
            },
            "triage": self._triage_options(pet),
            "nearby": self._local.notices(pet) if self._local else [],
            "costs": {
                "estimates": [self._estimate(e, plan if member else None) for e in self._open(pet)],
                "year": year,
                "payment_options": self._practice.payment_options(),
            },
            "visit": self._visit(pet),
            "due": self._due(pet),
            "pathway": self._pathway(pet) if pathway.is_young(pet, self._today) else None,
            "checkin": self._checkin(pet) if stage == "senior" else None,
        }

    # Commands ----------------------------------------------------------------
    def check_in(self, pet_id: str, scores: dict[str, int]) -> dict:
        self.pet(pet_id)
        try:
            clean = ci.validate(scores)
        except ValueError as exc:
            raise DashboardError(str(exc)) from exc
        self._store.save_checkin(pet_id, ci.iso_week(self._today), clean)
        return self.dashboard(pet_id)

    def triage(self, pet_id: str, symptom: str, hours: int, eating: bool, bright: bool) -> dict:
        """TR-1 to TR-5: route, log the answer, and return what the owner should do."""
        pet = self.pet(pet_id)
        if pet.species not in tr.SPECIES:
            raise DashboardError(f"For {pet.species}s, please call the clinic.")
        try:
            result = tr.route(symptom, hours, eating, bright)
        except ValueError as exc:
            raise DashboardError(str(exc)) from exc
        self._store.log_triage(pet_id, symptom, hours, result.level.value)
        return {
            "level": result.level.value,
            "headline": result.headline,
            "advice": result.advice,
            "symptom": tr.BY_KEY[symptom].label,
            "duration": dict(tr.DURATIONS)[hours],
        }

    def tick(self, pet_id: str, item: str, done: bool) -> dict:
        """VR-2, NP-1: the owner marks an instruction or a home step done."""
        self.pet(pet_id)
        if item not in self._tickable(pet_id):
            raise DashboardError("That isn't something you can tick off")
        self._store.set_tick(pet_id, item, done)
        return self.dashboard(pet_id)

    def estimate(self, pet_id: str, estimate_id: str) -> Estimate:
        pet = self.pet(pet_id)
        match = next((e for e in self._open(pet) if e.id == estimate_id), None)
        if match is None:
            raise DashboardError("That estimate isn't open any more")
        return match

    def recap(self, pet_id: str, recap_id: str) -> recaps.Recap:
        self.pet(pet_id)
        match = next((r for r in self._recaps(pet_id) if r.id == recap_id), None)
        if match is None:
            raise DashboardError("That visit summary isn't available")
        return match

    # Sections ----------------------------------------------------------------
    def _triage_options(self, pet: Pet) -> dict:
        return {
            "available": pet.species in tr.SPECIES,
            "symptoms": [
                {"key": s.key, "label": s.label, "red_flag": s.red_flag} for s in tr.SYMPTOMS
            ],
            "durations": [{"hours": h, "label": label} for h, label in tr.DURATIONS],
        }

    def _open(self, pet: Pet) -> list[Estimate]:
        """CO-1: open estimates the clinic has sent, in the clinic's own words (CL-7)."""
        released = self._store.estimate_releases()
        sent = [
            sent_version(e, released[e.id]["explanations"])
            for e in self._practice.estimates(pet.id)
            if e.id in released
        ]
        return open_estimates(sent, self._today)

    def _estimate(self, estimate: Estimate, plan: Plan | None) -> dict:
        price = owner_price(estimate, plan)
        return {
            "id": estimate.id,
            "title": estimate.title,
            "vet": estimate.vet,
            "given": f"{estimate.created.day} {estimate.created:%b}",
            "valid_until": f"{estimate.expires.day} {estimate.expires:%b}",
            "plan": plan.name if plan else None,
            "lines": [
                {
                    "name": line.name,
                    "explanation": line.explanation,
                    "low": line.low,
                    "high": line.high,
                    "optional": line.optional,
                    "included": line.name in price.included_lines,
                }
                for line in estimate.lines
            ],
            "recommended": {"low": price.recommended.low, "high": price.recommended.high},
            "with_optional": {"low": price.with_optional.low, "high": price.with_optional.high},
            "included": price.included,
        }

    def _visit(self, pet: Pet) -> dict | None:
        recap = recaps.latest(self._recaps(pet.id), self._today)
        if recap is None:
            return None
        ticked = self._store.ticks(pet.id)
        return {
            "id": recap.id,
            "date": f"{recap.visit:%A} {recap.visit.day} {recap.visit:%b}",
            "vet": recap.vet,
            "summary": recap.summary,
            "instructions": [
                {
                    "key": f"{recap.id}:{i}",
                    "text": step.text,
                    "progress": recaps.progress(step, recap.visit, self._today),
                    "done": f"{recap.id}:{i}" in ticked,
                }
                for i, step in enumerate(recap.instructions)
            ],
            "results": [
                {"name": r.name, "status": r.status, "comment": r.comment} for r in recap.results
            ],
            "follow_up": recap.follow_up,
            "follow_up_when": recaps.follow_up_label(recap, self._today),
        }

    def _due(self, pet: Pet) -> list[dict]:
        events, prices = self._practice.events(pet.id), self._practice.price_list()
        return [
            {
                "title": g.title,
                "due_label": due_label(g, self._today),
                "status": g.status.value,
                "value": g.value,
            }
            for g in rank_by_value(find_gaps(pet, events, prices, self._today))
        ]

    def _pathway(self, pet: Pet) -> dict:
        given = [e.date for e in self._practice.events(pet.id) if e.type == "vaccination"]
        ticked = self._store.ticks(pet.id)
        _, member, year = self._year_ahead(pet)
        steps = pathway.vaccine_steps(pet, given, self._today) + pathway.home_steps(
            pet, ticked, self._today
        )
        return {
            "weeks_old": pathway.weeks_old(pet, self._today),
            "tip": pathway.tip(pet, self._today),
            "steps": [
                {
                    "key": s.key,
                    "title": s.title,
                    "detail": s.detail,
                    "done": s.done,
                    "when": s.when,
                    "owner_ticks": s.owner_ticks,
                }
                for s in steps
            ],
            "plan_offer": None if member else year["plan"],
        }

    def _checkin(self, pet: Pet) -> dict:
        history = [ci.CheckIn(w, s) for w, s in self._store.checkins(pet.id)]
        week = ci.iso_week(self._today)
        latest = history[-1] if history else None
        trend = ci.trend(history, self._today)
        return {
            "questions": [
                {"key": k, "question": q, "low": lo, "high": hi} for k, q, lo, hi in ci.QUESTIONS
            ],
            "week": week,
            "done_this_week": bool(latest and latest.week == week),
            "latest": latest.scores if latest else None,
            "max_total": ci.MAX_SCORE * len(ci.QUESTIONS),
            "history": [
                {"week": w.week, "total": w.total, "low": w.low}
                for w in ci.recent_weeks(history, self._today)
            ],
            "trend": {"dropping": trend.dropping, "message": ci.describe(trend)},
            "shared": self._store.consent(self._owner_id).share_log,
        }

    def _year_ahead(self, pet: Pet) -> tuple[Plan | None, bool, dict]:
        """HT-4: the next 12 months, on the pet's plan or the one for its life stage."""
        prices = self._practice.price_list()
        dues = upcoming_care(pet, self._practice.events(pet.id), prices)
        dues += self._course_doses(pet, prices["vaccination"])
        result = forecast(dues, self._today)
        plan, member = self._plan_for(pet, result)
        cost = result.on_plan(plan) if plan else None
        year = {
            "items": [
                {
                    "month": _month(i.due, self._today),
                    "title": i.title.removesuffix(" due"),
                    "price": i.price,
                    "overdue": i.overdue,
                    "included": bool(plan and i.type in plan.covers),
                }
                for i in result.items
            ],
            "pay_as_you_go": result.pay_as_you_go,
            "plan": cost
            and {
                "name": cost.plan_name,
                "member": member,
                "fees": cost.fees,
                "extras": cost.extras,
                "total": cost.total,
                "saving": result.pay_as_you_go - cost.total,
                "monthly_price": plan.monthly_price,
                "benefits": plan.benefits,
            },
        }
        return plan, member, year

    def _course_doses(self, pet: Pet, price: int) -> list[Due]:
        """NP-1: a young pet's remaining course doses belong in its year ahead (HT-4)."""
        if not pathway.is_young(pet, self._today):
            return []
        given = [e.date for e in self._practice.events(pet.id) if e.type == "vaccination"]
        return [
            Due(GapType.VACCINATION, s.title, "", s.due, price)
            for s in pathway.vaccine_steps(pet, given, self._today)
            if s.due is not None
        ]

    def _plan_for(self, pet: Pet, result: Forecast) -> tuple[Plan | None, bool]:
        """The pet's own plan; otherwise the cheapest plan meant for its life stage."""
        plans = {p.id: p for p in self._practice.plans()}
        membership = next((m for m in self._practice.memberships() if m.pet_id == pet.id), None)
        if membership and membership.plan_id in plans:
            return plans[membership.plan_id], True
        stage = life_stage(pet, self._today)
        eligible = [
            p
            for p in plans.values()
            if p.life_stage in (None, stage) and (not p.species or pet.species in p.species)
        ]
        best = min(eligible, key=lambda p: result.on_plan(p).total, default=None)
        return best, False

    def _recaps(self, pet_id: str) -> list[recaps.Recap]:
        return [recaps.from_record(pet_id, r) for r in self._store.recaps(pet_id)]

    def _tickable(self, pet_id: str) -> set[str]:
        keys = {key for key, _, _ in pathway.HOME_STEPS} | {"desexing"}
        for recap in self._recaps(pet_id):
            keys |= {f"{recap.id}:{i}" for i in range(len(recap.instructions))}
        return keys


def _month(day: date, today: date) -> str:
    """A 12-month horizon can hold the same month twice, so later years carry a year."""
    return f"{day:%b}" if day.year == today.year else f"{day:%b} '{day:%y}"
