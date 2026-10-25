"""Tools the care agent can call.

Read tools return facts from the pet's records. Action tools that contact the clinic only
create a proposal (AG-4); the owner confirms it in the UI. Each tool may also return a
`card` the UI renders, and a `trace` label shown as "What I did" (AG-7).
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from vetagent.domain.care_gaps import due_label, find_gaps, rank_by_value, short_date
from vetagent.domain.plan_value import plan_value
from vetagent.integrations.practice import PracticeSystem
from vetagent.store.sqlite import Store


@dataclass(frozen=True)
class ToolContext:
    owner_id: str
    pet_id: str
    practice: PracticeSystem
    store: Store
    today: date


@dataclass(frozen=True)
class ToolOutput:
    result: dict[str, Any]
    card: dict[str, Any] | None = None


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_schema: dict[str, Any]
    trace: str
    run: Callable[[ToolContext, dict[str, Any]], ToolOutput]


NO_INPUT = {"type": "object", "properties": {}}


def _pet_basics(ctx: ToolContext) -> dict[str, str]:
    pet = ctx.practice.pet(ctx.pet_id)
    owner = ctx.practice.owner(pet.owner_id)
    return {"pet": pet.name, "owner": owner.name.split(" ")[0], "vet": ctx.practice.lead_vet()}


def _care_items(ctx: ToolContext) -> list[dict[str, Any]]:
    pet = ctx.practice.pet(ctx.pet_id)
    gaps = find_gaps(pet, ctx.practice.events(pet.id), ctx.practice.price_list(), ctx.today)
    return [
        {
            "type": g.type.value,
            "title": g.title,
            "reason": g.reason,
            "status": g.status.value,
            "due_label": due_label(g, ctx.today),
            "value": g.value,
        }
        for g in rank_by_value(gaps)
    ]


def list_care_due(ctx: ToolContext, _: dict[str, Any]) -> ToolOutput:
    items = _care_items(ctx)
    card = {"type": "care_due", "items": items} if items else None
    return ToolOutput({**_pet_basics(ctx), "items": items}, card)


def get_plan_value(ctx: ToolContext, _: dict[str, Any]) -> ToolOutput:
    membership = next((m for m in ctx.practice.memberships() if m.pet_id == ctx.pet_id), None)
    if membership is None:
        return ToolOutput({**_pet_basics(ctx), "member": False})
    plan = next(p for p in ctx.practice.plans() if p.id == membership.plan_id)
    value = plan_value(membership, plan, ctx.practice.benefit_uses(ctx.pet_id), ctx.today)
    included = [i for i in _care_items(ctx) if i["type"] in plan.covers]
    result = {
        **_pet_basics(ctx),
        "member": True,
        "plan": value.plan_name,
        "monthly_price": value.monthly_price,
        "months_paid": value.months_paid,
        "paid": value.paid,
        "benefits_used": value.benefits_used,
        "balance": value.balance,
        "included_care_due": [{"title": i["title"], "value": i["value"]} for i in included],
    }
    card = {
        "type": "plan_value",
        **{k: result[k] for k in ("plan", "monthly_price", "months_paid", "paid", "benefits_used")},
    }
    return ToolOutput(result, card)


def get_visit_history(ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
    limit = int(args.get("limit", 5))
    events = [e for e in ctx.practice.events(ctx.pet_id) if e.type != "weight"]
    recent = sorted(events, key=lambda e: e.date, reverse=True)[:limit]
    visits = [{"date": short_date(e.date), "type": e.type, "detail": e.detail} for e in recent]
    return ToolOutput({**_pet_basics(ctx), "visits": visits})


def log_weight(ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
    kg = round(float(args["kg"]), 1)
    if not 0.5 <= kg <= 120:
        return ToolOutput({"error": f"{kg} kg looks wrong; ask the owner to check the number."})
    shared = ctx.store.consent(ctx.owner_id).share_log  # AG-5
    ctx.store.log_weight(ctx.pet_id, kg, shared)
    history = [(e.date, e.kg) for e in ctx.practice.events(ctx.pet_id) if e.type == "weight"]
    points = [{"label": f"{d:%b}", "kg": w} for d, w in history[-3:]] + [
        {"label": "Today", "kg": kg}
    ]
    first = history[0] if history else (ctx.today, kg)
    result = {
        **_pet_basics(ctx),
        "kg": kg,
        "change_kg": round(kg - first[1], 1),
        "since": f"{first[0]:%B}",
        "shared_with_clinic": shared,
    }
    return ToolOutput(result, {"type": "weight", "kg": kg, "points": points, "shared": shared})


def propose_booking(ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
    reason = str(args.get("reason") or "Check-up")
    preferred = str(args.get("preferred_time") or "any time")
    proposal = ctx.store.create_proposal(
        ctx.owner_id,
        "booking_request",
        {"pet_id": ctx.pet_id, "reason": reason, "preferred_time": preferred},
    )
    card = {
        "type": "proposal",
        "proposal_id": proposal.id,
        "title": "Booking request",
        "detail": f"{reason} · {preferred}",
        "action": "Send to clinic",
    }
    return ToolOutput(
        {**_pet_basics(ctx), "status": "awaiting owner confirmation", "reason": reason}, card
    )


def propose_vet_note(ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
    note = str(args["note"]).strip()
    proposal = ctx.store.create_proposal(
        ctx.owner_id, "vet_note", {"pet_id": ctx.pet_id, "note": note}
    )
    basics = _pet_basics(ctx)
    card = {
        "type": "proposal",
        "proposal_id": proposal.id,
        "title": f"Note for {basics['vet']}",
        "detail": note,
        "action": f"Send to {basics['vet']}",
    }
    return ToolOutput({**basics, "status": "awaiting owner confirmation"}, card)


def propose_estimate_reply(ctx: ToolContext, args: dict[str, Any]) -> ToolOutput:
    """CO-3: the owner's answer to a clinic estimate, prepared for them to confirm."""
    wanted = str(args["estimate_id"])
    estimate = next((e for e in ctx.practice.estimates(ctx.pet_id) if e.id == wanted), None)
    if estimate is None:
        raise ValueError(f"No open estimate {wanted}")
    choice = str(args["choice"])
    if choice == "accept":
        chosen = {str(n) for n in args.get("optional_lines") or []}
        lines = [line.name for line in estimate.lines if not line.optional or line.name in chosen]
        detail = f"Go ahead with {estimate.title.lower()}: {', '.join(lines)}"
    elif choice == "cheaper":
        detail = f"Is there a lower-cost option for {estimate.title.lower()}?"
    elif choice == "question":
        detail = f"Question about {estimate.title.lower()}: {str(args['question']).strip()}"
    else:
        raise ValueError(f"Unknown choice {choice}")
    proposal = ctx.store.create_proposal(
        ctx.owner_id,
        "estimate_reply",
        {"pet_id": ctx.pet_id, "estimate_id": estimate.id, "choice": choice, "detail": detail},
    )
    card = {
        "type": "proposal",
        "proposal_id": proposal.id,
        "title": f"Reply to {estimate.vet}'s estimate",
        "detail": detail,
        "action": "Send to clinic",
    }
    return ToolOutput({**_pet_basics(ctx), "status": "awaiting owner confirmation"}, card)


TOOLS: list[Tool] = [
    Tool(
        "list_care_due",
        "List care that is overdue or due soon for the pet, with value.",
        NO_INPUT,
        "checked care due",
        list_care_due,
    ),
    Tool(
        "get_plan_value",
        "Compare plan payments so far with benefits used this plan year.",
        NO_INPUT,
        "checked plan payments and benefits",
        get_plan_value,
    ),
    Tool(
        "get_visit_history",
        "Recent clinic records: vaccinations, consults, findings.",
        {
            "type": "object",
            "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 10}},
        },
        "read visit history",
        get_visit_history,
    ),
    Tool(
        "log_weight",
        "Save a weight the owner measured at home.",
        {"type": "object", "properties": {"kg": {"type": "number"}}, "required": ["kg"]},
        "added to health log",
        log_weight,
    ),
    Tool(
        "propose_booking",
        "Prepare a booking request for the owner to confirm. Nothing is sent until they do.",
        {
            "type": "object",
            "properties": {
                "reason": {"type": "string"},
                "preferred_time": {"type": "string", "description": "e.g. 'mornings'"},
            },
            "required": ["reason"],
        },
        "prepared a booking request",
        propose_booking,
    ),
    Tool(
        "propose_vet_note",
        "Draft a short factual note to the vet about a non-urgent concern, "
        "for the owner to confirm.",
        {"type": "object", "properties": {"note": {"type": "string"}}, "required": ["note"]},
        "drafted a note for the vet",
        propose_vet_note,
    ),
    Tool(
        "propose_estimate_reply",
        "Prepare the owner's reply to an open clinic estimate: accept it (with any optional "
        "lines they chose), ask for a lower-cost option, or ask a question. Never say whether "
        "a line is clinically needed.",
        {
            "type": "object",
            "properties": {
                "estimate_id": {"type": "string"},
                "choice": {"type": "string", "enum": ["accept", "cheaper", "question"]},
                "optional_lines": {"type": "array", "items": {"type": "string"}},
                "question": {"type": "string"},
            },
            "required": ["estimate_id", "choice"],
        },
        "prepared a reply to the estimate",
        propose_estimate_reply,
    ),
]

TOOLS_BY_NAME = {t.name: t for t in TOOLS}


def run_tool(name: str, args: dict[str, Any], ctx: ToolContext) -> ToolOutput:
    tool = TOOLS_BY_NAME.get(name)
    if tool is None:
        return ToolOutput({"error": f"Unknown tool {name}"})
    try:
        return tool.run(ctx, args)
    except (KeyError, ValueError, TypeError) as exc:
        return ToolOutput({"error": f"Bad input for {name}: {exc}"})
