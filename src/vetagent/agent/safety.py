"""Deterministic safety gate (docs/requirements.md AG-3).

Runs before the model. Urgent symptoms never reach the LLM: the owner is told to call
the clinic now. Keep this list conservative and reviewed by a vet.
"""

import re
from dataclasses import dataclass

URGENT_PATTERNS = {
    "not using a leg": r"(not|isn'?t|won'?t|can'?t) (putting|bearing|put|bear) (any )?weight"
    r"|holding (it|his|her|their|the|a) (leg|paw) up",
    "collapse": r"collaps|can'?t (stand|get up)|unconscious|unresponsive",
    "seizure": r"seizure|fitting|convuls",
    "breathing": r"can'?t breathe|cannot breathe|struggling to breathe|gasping|blue gums",
    "bleeding": r"bleeding (a lot|heavily|badly)|won'?t stop bleeding",
    "poisoning": r"poison|rat bait|snail bait|ate (chocolate|lilies|grapes|raisins)",
    "trauma": r"hit by a car|hit by car",
    "bloat": r"bloated|swollen (belly|stomach)|retching (but|and) nothing",
}


@dataclass(frozen=True)
class Triage:
    urgent: bool
    reason: str = ""


def triage(text: str) -> Triage:
    lowered = text.lower()
    for reason, pattern in URGENT_PATTERNS.items():
        if re.search(pattern, lowered):
            return Triage(urgent=True, reason=reason)
    return Triage(urgent=False)


def urgent_reply(clinic: str, pet: str) -> str:
    return (
        f"That can need same-day care. Please call {clinic} now rather than waiting for a "
        f"reply here. If they're closed, go to your nearest emergency vet with {pet}."
    )
