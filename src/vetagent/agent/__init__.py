"""Pet-owner care agent: one small loop, a set of tools, a safety gate and a model adapter.

Message format used everywhere inside the agent (provider-neutral, stored as JSON):
    {"role": "user", "text": str}
    {"role": "assistant", "text": str, "tool_calls": [{"id", "name", "args"}], "cards": [...]}
    {"role": "tool", "tool_call_id": str, "name": str, "result": dict, "card": dict | None}
Model adapters translate this to their provider's format.
"""
