"""12-month care cost forecast (docs/requirements.md HT-4).

Projects each `Due` from the care-gap rules over the next year, priced from the clinic's price
list (CG-6), then totals it pay-as-you-go and on a plan. Overdue care is placed in this month.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

from vetagent.domain.care_gaps import Due
from vetagent.domain.models import Plan

HORIZON_DAYS = 365


@dataclass(frozen=True)
class ForecastItem:
    due: date
    title: str
    type: str
    price: int
    overdue: bool


@dataclass(frozen=True)
class PlanCost:
    plan_name: str
    fees: int  # 12 monthly payments
    extras: int  # care the plan does not include
    included: int  # list price of care the plan includes

    @property
    def total(self) -> int:
        return self.fees + self.extras


@dataclass(frozen=True)
class Forecast:
    items: list[ForecastItem]
    pay_as_you_go: int

    def on_plan(self, plan: Plan) -> PlanCost:
        included = sum(i.price for i in self.items if i.type in plan.covers)
        return PlanCost(
            plan_name=plan.name,
            fees=plan.monthly_price * 12,
            extras=self.pay_as_you_go - included,
            included=included,
        )


def forecast(dues: Iterable[Due], today: date) -> Forecast:
    end = today + timedelta(days=HORIZON_DAYS)
    items = []
    for due in dues:
        day, overdue = max(due.due_date, today), due.due_date < today
        while day < end:
            items.append(ForecastItem(day, due.title, due.type.value, due.value, overdue))
            if not due.every_days:
                break
            day, overdue = day + timedelta(days=due.every_days), False
    items.sort(key=lambda i: (i.due, -i.price))
    return Forecast(items, sum(i.price for i in items))
