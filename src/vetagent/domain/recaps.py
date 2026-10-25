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


STATUSES = ("normal", "follow_up")
MAX_ITEMS = 10


def build(
    recap_id: str,
    pet_id: str,
    visit: date,
    vet: str,
    summary: str,
    instructions: list[Instruction],
    results: list[Result],
    follow_up: str,
    follow_up_by: date | None,
    today: date,
) -> Recap:
    """CL-8: a recap the clinic writes; refuse anything the owner couldn't use."""
    if visit > today:
        raise ValueError("The visit date can't be in the future")
    if visit < today - timedelta(days=60):
        raise ValueError("Owners only see visits from the last 60 days")
    if not summary.strip():
        raise ValueError("Write a short summary for the owner")
    if len(instructions) > MAX_ITEMS or len(results) > MAX_ITEMS:
        raise ValueError(f"Keep it to {MAX_ITEMS} instructions and {MAX_ITEMS} results")
    for step in instructions:
        if not step.text.strip():
            raise ValueError("An instruction is empty")
        if step.days is not None and not 1 <= step.days <= 90:
            raise ValueError("Instruction length must be 1 to 90 days")
    for result in results:
        if not result.name.strip() or not result.comment.strip():
            raise ValueError("Each result needs a name and the vet's comment")
        if result.status not in STATUSES:
            raise ValueError(f"Result status must be one of {', '.join(STATUSES)}")
    if follow_up_by is not None and (follow_up_by < visit or not follow_up.strip()):
        raise ValueError("A follow-up date needs a follow-up, on or after the visit")
    return Recap(
        recap_id,
        pet_id,
        visit,
        vet,
        summary.strip(),
        [Instruction(i.text.strip(), i.days) for i in instructions],
        [Result(r.name.strip(), r.status, r.comment.strip()) for r in results],
        follow_up.strip(),
        follow_up_by,
    )


def to_record(recap: Recap) -> dict:
    """The stored shape, also used by data/demo_home.json."""
    return {
        "id": recap.id,
        "visit": recap.visit.isoformat(),
        "vet": recap.vet,
        "summary": recap.summary,
        "instructions": [{"text": i.text, "days": i.days} for i in recap.instructions],
        "results": [
            {"name": r.name, "status": r.status, "comment": r.comment} for r in recap.results
        ],
        "follow_up": recap.follow_up,
        "follow_up_by": recap.follow_up_by.isoformat() if recap.follow_up_by else None,
    }


def from_record(pet_id: str, raw: dict) -> Recap:
    follow_by = raw.get("follow_up_by")
    return Recap(
        id=raw["id"],
        pet_id=pet_id,
        visit=date.fromisoformat(raw["visit"]),
        vet=raw["vet"],
        summary=raw["summary"],
        instructions=[Instruction(i["text"], i.get("days")) for i in raw["instructions"]],
        results=[Result(r["name"], r["status"], r["comment"]) for r in raw["results"]],
        follow_up=raw.get("follow_up", ""),
        follow_up_by=date.fromisoformat(follow_by) if follow_by else None,
    )
