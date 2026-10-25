"""Registered product labels from the APVMA register (docs/requirements.md OD-2).

The clinic links each parasite product it sells to its APVMA registration. This checks the
registration is current and that the label covers every species the product was dispensed to:
some dog flea products can kill a cat. It reads the label; it never suggests a medicine.
"""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Label:
    product_id: str  # the clinic's own product (ezyVet product id)
    apvma_number: str
    name: str
    registrant: str
    expires: date
    uses: dict[str, list[str]]  # species -> pests the label lists, e.g. {"dog": ["paralysis tick"]}


@dataclass(frozen=True)
class LabelCheck:
    label: Label
    current: bool
    given_to: list[str]  # species the clinic dispensed it to
    off_label: list[str]  # of those, species the label doesn't list


def check_label(label: Label, given_to: set[str], today: date) -> LabelCheck:
    """OD-2: current registration, and every species it was dispensed to is on the label."""
    return LabelCheck(
        label=label,
        current=label.expires >= today,
        given_to=sorted(given_to),
        off_label=sorted(s for s in given_to if s not in label.uses),
    )
