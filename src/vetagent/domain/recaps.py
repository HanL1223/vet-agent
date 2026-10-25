"""Visit recaps the clinic releases to owners (docs/requirements.md VR-1 to VR-3).

The clinic writes the recap in plain language; this module only works out where the owner is
in each instruction ("day 6 of 14") and whether the follow-up is due.
"""

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class Instruction:
    text: str
    days: int | None = None  # how long it lasts from the visit; None: a one-off task


@dataclass(frozen=True)
class Result:
    name: str
    status: str  # "normal" or "follow_up", in the vet's own judgement
    comment: str  # the vet's words, shown as written


@dataclass(frozen=True)
class Recap:
    id: str
    pet_id: str
    visit: date
    vet: str
    summary: str
    instructions: list[Instruction]
    results: list[Result]
    follow_up: str
    follow_up_by: date | None


def progress(instruction: Instruction, visit: date, today: date) -> str:
    """'Day 6 of 14' while it runs, 'Finished' after; empty for one-off tasks."""
    if instruction.days is None:
        return ""
    day = (today - visit).days + 1
    if day > instruction.days:
        return "Finished"
    return f"Day {max(day, 1)} of {instruction.days}"


def follow_up_label(recap: Recap, today: date) -> str:
    if recap.follow_up_by is None:
        return ""
    days = (recap.follow_up_by - today).days
    if days < 0:
        return f"was due {recap.follow_up_by.day} {recap.follow_up_by:%b}"
    if days <= 7:
        return f"by {recap.follow_up_by:%A} {recap.follow_up_by.day} {recap.follow_up_by:%b}"
    return f"by {recap.follow_up_by.day} {recap.follow_up_by:%b}"


def latest(
    recaps: list[Recap], today: date, within: timedelta = timedelta(days=60)
) -> Recap | None:
    """The newest recap from the last two months; older visits drop off the dashboard."""
    recent = [r for r in recaps if today - within <= r.visit <= today]
    return max(recent, key=lambda r: r.visit, default=None)
