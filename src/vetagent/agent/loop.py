"""The agent loop: safety gate, then reason -> act -> repeat until the model answers."""

from vetagent.agent.llm import Model
from vetagent.agent.safety import triage, urgent_reply
from vetagent.agent.tools import TOOLS, ToolContext, run_tool

MAX_STEPS = 6
GIVE_UP = "Sorry, I couldn't finish that. Please try again, or call the clinic if it's urgent."


def run_turn(
    model: Model, system: str, history: list[dict], user_text: str, ctx: ToolContext
) -> list[dict]:
    """Returns the new messages for this turn (user message first)."""
    new: list[dict] = [{"role": "user", "text": user_text}]

    check = triage(user_text)  # AG-3: urgent symptoms never reach the model
    if check.urgent:
        clinic, pet = ctx.practice.clinic_name(), ctx.practice.pet(ctx.pet_id).name
        new.append(
            {
                "role": "assistant",
                "text": urgent_reply(clinic, pet),
                "cards": [{"type": "urgent", "clinic": clinic, "reason": check.reason}],
            }
        )
        return new

    for _ in range(MAX_STEPS):
        reply = model.reply(system, history + new, TOOLS)
        new.append(
            {
                "role": "assistant",
                "text": reply.text,
                "tool_calls": [
                    {"id": c.id, "name": c.name, "args": c.args} for c in reply.tool_calls
                ],
            }
        )
        if not reply.tool_calls:
            return new
        for call in reply.tool_calls:
            output = run_tool(call.name, call.args, ctx)
            new.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": call.name,
                    "result": output.result,
                    "card": output.card,
                }
            )

    new.append({"role": "assistant", "text": GIVE_UP})
    return new
