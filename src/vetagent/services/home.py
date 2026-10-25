"""Owner pet dashboard use cases: weekly check-ins, preventive cover and the cost forecast.

Clinic records come from the practice system; check-ins and owner-given doses are app-owned
data in the store (PR-3). Nothing here contacts the clinic; a check-up request goes through the
owner agent's proposal flow (AG-4).
"""

from datetime import date

from vetagent.domain import checkins as ci
from vetagent.domain.care_gaps import (
    due_label,
    find_gaps,
    life_stage,
    rank_by_value,
    upcoming_care,
)
from vetagent.domain.cover import WINDOW_DAYS, Dose, cover
from vetagent.domain.forecast import Forecast, forecast
from vetagent.domain.models import Plan
from vetagent.integrations.practice import PracticeSystem
from vetagent.store.sqlite import Store


class DashboardError(ValueError):
    pass


class HomeService:
    def __init__(
        self, practice: PracticeSystem, store: Store, today: date, owner_id: str, pet_id: str
    ) -> None:
        self._practice = practice
        self._store = store
        self._today = today
        self._owner_id = owner_id
        self._pet_id = pet_id

    # Queries -----------------------------------------------------------------
    def dashboard(self) -> dict:
        pet = self._practice.pet(self._pet_id)
        return {
            "clinic": self._practice.clinic_name(),
            "owner": self._practice.owner(self._owner_id).name.split(" ")[0],
            "pet": {
                "name": pet.name,
                "species": pet.species,
                "breed": pet.breed,
                "age": pet.age_on(self._today),
            },
            "household": self.household(),
            "due": self._due(),
            "checkin": self._checkin(),
            "cover": self._cover(),
            "forecast": self._forecast(),
            "weight": self._weight(),
        }

    def household(self) -> list[str]:
        """BR-1: species of every pet this owner registered; the page picks one for its mark."""
        return sorted({p.species for p in self._practice.pets() if p.owner_id == self._owner_id})

    # Commands ----------------------------------------------------------------
    def check_in(self, scores: dict[str, int]) -> dict:
        try:
            clean = ci.validate(scores)
        except ValueError as exc:
            raise DashboardError(str(exc)) from exc
        self._store.save_checkin(self._pet_id, ci.iso_week(self._today), clean)
        return self.dashboard()

    def log_dose(self, product: str) -> dict:
        """HT-6: owner-given doses only; injections are given at the clinic."""
        givable = {p.label for p in self._practice.parasite_products() if p.owner_given}
        if product not in givable:
            raise DashboardError(f"{product} isn't something you give at home")
        self._store.log_dose(self._pet_id, product, self._today.isoformat())
        return self.dashboard()

    # Tiles -------------------------------------------------------------------
    def _due(self) -> list[dict]:
        pet = self._practice.pet(self._pet_id)
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

    def _checkin(self) -> dict:
        history = [ci.CheckIn(w, s) for w, s in self._store.checkins(self._pet_id)]
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

    def _cover(self) -> list[dict]:
        products = {p.label: p for p in self._practice.parasite_products()}
        doses = [
            Dose(e.detail, e.date, e.repeat_days or products[e.detail].lasts_days)
            for e in self._practice.events(self._pet_id)
            if e.type == "parasite" and e.detail in products
        ]
        doses += [
            Dose(product, date.fromisoformat(given), products[product].lasts_days, True)
            for product, given in self._store.owner_doses(self._pet_id)
            if product in products
        ]
        return [
            {
                "product": c.product,
                "percent": c.percent,
                "days_left": c.days_left,
                "last_given": f"{c.last_given.day} {c.last_given:%b}",
                "owner_reported": c.owner_reported,
                "can_log": products[c.product].owner_given,
                "spans": c.spans,
                "window_days": WINDOW_DAYS,
            }
            for c in cover(doses, self._today)
        ]

    def _forecast(self) -> dict:
        pet = self._practice.pet(self._pet_id)
        dues = upcoming_care(pet, self._practice.events(pet.id), self._practice.price_list())
        result = forecast(dues, self._today)
        plan, member = self._plan_for_forecast(result)
        cost = result.on_plan(plan) if plan else None
        return {
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
            },
        }

    def _plan_for_forecast(self, result: Forecast) -> tuple[Plan | None, bool]:
        """The pet's own plan; otherwise the cheapest plan meant for its life stage."""
        plans = {p.id: p for p in self._practice.plans()}
        membership = next(
            (m for m in self._practice.memberships() if m.pet_id == self._pet_id), None
        )
        if membership and membership.plan_id in plans:
            return plans[membership.plan_id], True
        stage = life_stage(self._practice.pet(self._pet_id), self._today)
        eligible = [p for p in plans.values() if p.life_stage in (None, stage)]
        best = min(eligible, key=lambda p: result.on_plan(p).total, default=None)
        return best, False

    def _weight(self) -> dict | None:
        clinic = [(e.date, e.kg) for e in self._practice.events(self._pet_id) if e.type == "weight"]
        home = [
            (date.fromisoformat(w["logged_at"][:10]), w["kg"])
            for w in self._store.weights(self._pet_id)
        ]
        history = sorted(clinic + home)
        if not history:
            return None
        (first_day, first_kg), (_, latest_kg) = history[0], history[-1]
        return {
            "kg": latest_kg,
            "change_kg": round(latest_kg - first_kg, 1),
            "since": f"{first_day:%b %Y}",
            "points": [kg for _, kg in history[-6:]],
        }


def _month(day: date, today: date) -> str:
    """A 12-month horizon can hold the same month twice, so later years carry a year."""
    return f"{day:%b}" if day.year == today.year else f"{day:%b} '{day:%y}"
