from datetime import date

from conftest import TODAY

from vetagent.domain.care_gaps import find_gaps, rank_by_value
from vetagent.domain.models import CareEvent, GapStatus, GapType, Pet

PRICES = {
    "vaccination": 120,
    "parasite_repeat": 96,
    "heartworm": 160,
    "senior_screening": 280,
    "dental": 650,
}


def pet(species="dog", born=date(2020, 1, 1)) -> Pet:
    return Pet("x", "Rex", species, "Mixed", born, "o")


def gaps_for(p: Pet, events: list[CareEvent]):
    return find_gaps(p, events, PRICES, TODAY)


def test_cg1_vaccination_overdue_after_a_year():
    gaps = gaps_for(pet(), [CareEvent("x", "vaccination", date(2025, 10, 1), "C5 vaccine")])
    assert [(g.type, g.status) for g in gaps] == [(GapType.VACCINATION, GapStatus.OVERDUE)]


def test_cg1_no_history_no_gap():
    assert gaps_for(pet(), []) == []


def test_cg2_parasite_due_soon_uses_repeat_days():
    event = CareEvent(
        "x", "parasite", date(2026, 8, 1), "Chew", repeat_days=90, price_key="parasite_repeat"
    )
    [gap] = gaps_for(pet(), [event])
    assert gap.status is GapStatus.DUE_SOON and gap.due_date == date(2026, 10, 30)


def test_cg3_senior_due_on_senior_birthday_when_never_screened():
    [gap] = gaps_for(pet(born=date(2018, 11, 6)), [])
    assert gap.type is GapType.SENIOR and gap.due_date == date(2026, 11, 6)


def test_cg3_young_pet_has_no_senior_gap():
    assert gaps_for(pet(born=date(2023, 1, 1)), []) == []


def test_cg4_dental_cleared_by_later_procedure():
    events = [
        CareEvent("x", "finding", date(2026, 8, 1), "Tartar", finding="dental_recommended"),
        CareEvent("x", "dental", date(2026, 9, 1), "Scale and polish"),
    ]
    assert gaps_for(pet(), events) == []


def test_seed_clinic_has_eight_gaps_ranked_by_value(practice):
    gaps = rank_by_value(
        g
        for p in practice.pets()
        for g in find_gaps(p, practice.events(p.id), practice.price_list(), TODAY)
    )
    assert len(gaps) == 8
    assert gaps[0].type is GapType.DENTAL  # $650 first
