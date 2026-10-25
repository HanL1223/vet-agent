"""Model adapters (AG-8). The loop depends only on the `Model` protocol.

- `ClaudeModel` calls the Anthropic Messages API.
- `OpenAIModel` calls the OpenAI Chat Completions API.
- `ScriptedModel` is an offline, rule-based stand-in so the demo runs without an API key.
  It uses the same tools and the same loop, so the walkthrough exercises the real flow.
"""

import json
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol

from vetagent.agent.tools import Tool


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    args: dict[str, Any]


@dataclass(frozen=True)
class ModelReply:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)


class Model(Protocol):
    name: str

    def reply(self, system: str, messages: list[dict], tools: list[Tool]) -> ModelReply: ...


# --- Claude ----------------------------------------------------------------------


class ClaudeModel:
    def __init__(self, api_key: str, model: str, max_tokens: int = 600) -> None:
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens
        self.name = f"claude ({model})"

    def reply(self, system: str, messages: list[dict], tools: list[Tool]) -> ModelReply:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system,
            tools=[
                {"name": t.name, "description": t.description, "input_schema": t.input_schema}
                for t in tools
            ],
            messages=to_anthropic(messages),
        )
        text = "".join(b.text for b in response.content if b.type == "text")
        calls = [
            ToolCall(b.id, b.name, dict(b.input)) for b in response.content if b.type == "tool_use"
        ]
        return ModelReply(text.strip(), calls)


def to_anthropic(messages: list[dict]) -> list[dict]:
    """Neutral messages -> Anthropic format. Merges same-role neighbours; starts with user."""
    out: list[dict] = []
    for m in messages:
        if m["role"] == "user":
            role, blocks = "user", [{"type": "text", "text": m["text"]}]
        elif m["role"] == "assistant":
            role = "assistant"
            blocks = [{"type": "text", "text": m["text"]}] if m.get("text") else []
            blocks += [
                {"type": "tool_use", "id": c["id"], "name": c["name"], "input": c["args"]}
                for c in m.get("tool_calls", [])
            ]
        else:
            role = "user"
            blocks = [
                {
                    "type": "tool_result",
                    "tool_use_id": m["tool_call_id"],
                    "content": json.dumps(m["result"]),
                }
            ]
        if not blocks:
            continue
        if out and out[-1]["role"] == role:
            out[-1]["content"].extend(blocks)
        else:
            out.append({"role": role, "content": blocks})
    if out and out[0]["role"] != "user":
        out.insert(0, {"role": "user", "content": [{"type": "text", "text": "(opened the app)"}]})
    return out


# --- OpenAI ----------------------------------------------------------------------


class OpenAIModel:
    def __init__(self, api_key: str, model: str, max_tokens: int = 600) -> None:
        import openai

        self._client = openai.OpenAI(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens
        self.name = f"openai ({model})"

    def reply(self, system: str, messages: list[dict], tools: list[Tool]) -> ModelReply:
        response = self._client.chat.completions.create(
            model=self._model,
            max_completion_tokens=self._max_tokens,
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.input_schema,
                    },
                }
                for t in tools
            ],
            messages=[{"role": "system", "content": system}, *to_openai(messages)],
        )
        message = response.choices[0].message
        calls = [
            ToolCall(c.id, c.function.name, json.loads(c.function.arguments or "{}"))
            for c in message.tool_calls or []
        ]
        return ModelReply((message.content or "").strip(), calls)


def to_openai(messages: list[dict]) -> list[dict]:
    """Neutral messages -> OpenAI chat format. Tool args and results travel as JSON strings."""
    out: list[dict] = []
    for m in messages:
        if m["role"] == "user":
            out.append({"role": "user", "content": m["text"]})
        elif m["role"] == "assistant":
            calls = [
                {
                    "id": c["id"],
                    "type": "function",
                    "function": {"name": c["name"], "arguments": json.dumps(c["args"])},
                }
                for c in m.get("tool_calls", [])
            ]
            if not m.get("text") and not calls:
                continue  # card-only turns carry nothing for the model
            msg: dict = {"role": "assistant", "content": m.get("text") or None}
            if calls:
                msg["tool_calls"] = calls
            out.append(msg)
        else:
            out.append(
                {
                    "role": "tool",
                    "tool_call_id": m["tool_call_id"],
                    "content": json.dumps(m["result"]),
                }
            )
    return out


# --- Offline scripted model ----------------------------------------------------------

WEIGHT = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*kg")
SYMPTOMS = (
    "limp",
    "vomit",
    "diarrh",
    "itch",
    "scratch",
    "cough",
    "sneez",
    "not eating",
    "lethargic",
    "tired",
    "lump",
    "sore",
    "eye",
    "ear",
    "sick",
    "unwell",
)


class ScriptedModel:
    """Keyword intents in, tool calls out; fixed templates for the final reply."""

    name = "offline demo model"

    def reply(self, system: str, messages: list[dict], tools: list[Tool]) -> ModelReply:
        user_text = next(m["text"] for m in reversed(messages) if m["role"] == "user")
        turn = _current_turn(messages)
        results = {m["name"]: m["result"] for m in turn if m["role"] == "tool"}
        if not results:
            return self._first_step(user_text.lower())
        if "get_visit_history" in results and "propose_vet_note" not in results:
            note = _vet_note(user_text, results["get_visit_history"])
            return _call("propose_vet_note", {"note": note})
        return ModelReply(_final_text(results))

    def _first_step(self, text: str) -> ModelReply:
        if match := WEIGHT.search(text):
            return _call("log_weight", {"kg": float(match.group(1))})
        if "weigh" in text:
            return ModelReply('What did they weigh today? Type it like "31.2 kg" and I\'ll log it.')
        if any(s in text for s in SYMPTOMS):
            return _call("get_visit_history", {"limit": 5})
        if "book" in text or "appointment" in text:
            return _call(
                "propose_booking", {"reason": _booking_reason(text), "preferred_time": "mornings"}
            )
        if any(w in text for w in ("worth", "plan", "value", "save")):
            return _call("get_plan_value", {})
        if any(w in text for w in ("due", "next", "vaccin", "overdue", "need")):
            return _call("list_care_due", {})
        return ModelReply(
            "I can check what's due, request a booking, show what the care plan has paid for, "
            "log a weight, or pass a question to the vet. What would help?"
        )


def _call(name: str, args: dict[str, Any]) -> ModelReply:
    return ModelReply(tool_calls=[ToolCall(f"call_{uuid.uuid4().hex[:8]}", name, args)])


def _current_turn(messages: list[dict]) -> list[dict]:
    last_user = max(i for i, m in enumerate(messages) if m["role"] == "user")
    return messages[last_user + 1 :]


def _booking_reason(text: str) -> str:
    if "screen" in text or "blood" in text:
        return "Senior health screening"
    if "vaccin" in text:
        return "Vaccination"
    if "dental" in text or "teeth" in text:
        return "Dental check"
    return "Check-up"


def _vet_note(user_text: str, history: dict) -> str:
    consult = next((v for v in history["visits"] if v["type"] == "consult"), None)
    note = f'{history["owner"]} reports: "{user_text.strip()}".'
    if consult:
        note += f" Last consult {consult['date']}: {consult['detail']}"
    return note + f" Asks whether {history['pet']} needs a recheck."


def _final_text(results: dict[str, dict]) -> str:
    if "propose_vet_note" in results:
        r = results["propose_vet_note"]
        return (
            f"I can't diagnose, but I've drafted a note for {r['vet']} with {r['pet']}'s recent "
            "history and what you told me. Check it and tap send. If things get worse, call the "
            "clinic straight away."
        )
    if "propose_booking" in results:
        r = results["propose_booking"]
        return (
            f"I've prepared a booking request for {r['reason'].lower()}. Nothing goes to the "
            "clinic until you tap send."
        )
    if "log_weight" in results:
        r = results["log_weight"]
        if "error" in r:
            return "That weight looks off. Could you check the number?"
        change = (
            "no change"
            if r["change_kg"] == 0
            else f"{abs(r['change_kg'])} kg {'down' if r['change_kg'] < 0 else 'up'}"
        )
        shared = (
            f"I'll share it with {r['vet']} before the next visit."
            if r["shared_with_clinic"]
            else "Sharing with the clinic is off, so it stays in your log only."
        )
        return f"Saved {r['kg']} kg for {r['pet']}, {change} since {r['since']}. {shared}"
    if "get_plan_value" in results:
        r = results["get_plan_value"]
        if not r["member"]:
            return f"{r['pet']} isn't on a care plan yet. I can tell you what the plans include."
        text = (
            f"So far you've paid ${r['paid']} and {r['pet']} has used ${r['benefits_used']} "
            "of plan benefits."
        )
        if r["included_care_due"]:
            item = r["included_care_due"][0]
            ahead = r["balance"] + item["value"]
            text += (
                f" The {item['title'].lower()} is included and worth ${item['value']}, so booking "
                f"it would put you ${ahead} {'ahead' if ahead >= 0 else 'closer'}."
            )
        return text
    if "list_care_due" in results:
        r = results["list_care_due"]
        if not r["items"]:
            return f"Nothing is due for {r['pet']} right now."
        return f"Here's what's due for {r['pet']}. Want me to request a booking?"
    return "Done."
