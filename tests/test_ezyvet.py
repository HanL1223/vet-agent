from datetime import date

from vetagent.domain.care_gaps import find_gaps
from vetagent.integrations.ezyvet import FileSource, to_owner, unwrap

TODAY = date(2026, 10, 27)
BISCUIT, PEPPER, LUNA, ROCKET, MAX = "1201", "1202", "1204", "1205", "1209"


def test_unwrap_returns_records_inside_the_list_envelope():
    response = {"meta": {"items_page_total": 1}, "items": [{"animal": {"id": "1", "name": "Rex"}}]}
    assert unwrap(response) == [{"id": "1", "name": "Rex"}]


def test_demo_files_are_ezyvet_list_responses():
    animals = FileSource().list("v1/animal")
    assert {"id", "contact_id", "species_id", "breed_id", "date_of_birth", "is_dead"} <= set(
        animals[0]
    )


def test_CL6_deceased_animal_is_not_a_patient(practice):
    assert MAX not in {p.id for p in practice.pets()}
    assert practice.events(MAX) == []


def test_owner_is_shown_as_first_name_and_initial():
    assert to_owner({"id": 501, "first_name": "Priya", "last_name": "Sharma"}).name == "Priya S."


def test_epoch_dates_use_the_clinic_timezone(practice):
    assert practice.pet(BISCUIT).birth_date == date(2017, 6, 2)


def test_standard_of_care_parasite_keeps_its_interval_and_price(practice):
    event = next(e for e in practice.events(LUNA) if e.type == "parasite")
    assert (event.repeat_days, event.price_key) == (90, "parasite_repeat")


def test_due_dental_with_no_procedure_becomes_a_finding(practice):
    pepper = practice.pet(PEPPER)
    gaps = find_gaps(pepper, practice.events(PEPPER), practice.price_list(), TODAY)
    assert any(g.type == "dental" for g in gaps)


def test_only_active_memberships_count(practice):
    assert ROCKET not in {m.pet_id for m in practice.memberships()}
