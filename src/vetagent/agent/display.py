"""Turn stored agent messages into chat items for the UI.

Each agent item groups one reply: its text, the cards its tools produced, and a
"What I did" trace (AG-7). Proposal cards get their live status from the store.
"""

from collections.abc import Callable

from vetagent.agent.tools import TOOLS_BY_NAME


def to_chat_items(messages: list[dict], proposal_status: Callable[[str], str]) -> list[dict]:
    items: list[dict] = []
    for m in messages:
        if m["role"] == "user":
            items.append({"role": "user", "text": m["text"]})
            continue
        if not items or items[-1]["role"] != "agent":
            items.append({"role": "agent", "texts": [], "cards": [], "trace": []})
        item = items[-1]
        if m["role"] == "assistant":
            if m.get("text"):
                item["texts"].append(m["text"])
            item["cards"].extend(m.get("cards", []))
        elif m["role"] == "tool":
            tool = TOOLS_BY_NAME.get(m["name"])
            if tool and tool.trace not in item["trace"]:
                item["trace"].append(tool.trace)
            card = m.get("card")
            if card:
                if card["type"] == "proposal":
                    card = {**card, "status": proposal_status(card["proposal_id"])}
                item["cards"].append(card)
    return items
