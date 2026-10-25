"""Plan value for one pet (docs/requirements.md AG-6): benefits used vs payments made."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from vetagent.domain.models import BenefitUse, Membership, Plan


@dataclass(frozen=True)
class PlanValue:
    plan_name: str
    monthly_price: int
    months_paid: int
    paid: int
    benefits_used: int

    @property
    def balance(self) -> int:
        """Positive means the owner has received more than they paid."""
        return self.benefits_used - self.paid


def months_paid(start: date, today: date) -> int:
    """Payments are taken on the plan's start day each month, the first on `start`."""
    if today < start:
        return 0
    months = (today.year - start.year) * 12 + (today.month - start.month)
    return months + (1 if today.day >= start.day else 0)


def plan_value(
    membership: Membership, plan: Plan, uses: Iterable[BenefitUse], today: date
) -> PlanValue:
    paid_months = months_paid(membership.start, today)
    used = sum(
        u.value
        for u in uses
        if u.pet_id == membership.pet_id and membership.start <= u.date <= today
    )
    return PlanValue(
        plan_name=plan.name,
        monthly_price=plan.monthly_price,
        months_paid=paid_months,
        paid=paid_months * plan.monthly_price,
        benefits_used=used,
    )
