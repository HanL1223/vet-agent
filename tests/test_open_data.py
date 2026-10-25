"""Australian open data: registrations, labels, ticks, after-hours vet, heat (OD-1 to OD-6)."""

import json
from datetime import date

from vetagent.domain import local_area as la
from vetagent.domain.labels import Label, check_label
from vetagent.domain.models import ClinicContact
from vetagent.integrations import open_data_refresh as refresh
from vetagent.integrations.ezyvet import load_config
from vetagent.integrations.open_data import OpenData
from vetagent.services.local_area import LocalAreaService

TODAY = date(2026, 10, 27)
CONFIG = load_config()
SEASON = {1: 19, 2: 4, 3: 10, 4: 15, 5: 23, 6: 28, 7: 46, 8: 87, 9: 111, 10: 137, 11: 85, 12: 54}


def write(folder, name, body):
    source = {"publisher": "P", "licence": "L", "url": "u", "fetched": "2026-10-25"}
    (folder / f"{name}.json").write_text(json.dumps({"_source": source, **body}))


# OD-1: registrations --------------------------------------------------------------------


def test_od1_area_summary_counts_only_the_clinics_suburbs():
    rows = [
        la.SuburbPets("Kirwan", 100, 80, 20, 18),
        la.SuburbPets("Kelso", 50, 45, 10, 10),
        la.SuburbPets("Far Away", 999, 0, 0, 0),
    ]
    s = la.area_summary(rows, ["kirwan", "Kelso"])
    assert (s.dogs, s.cats, s.dogs_desexed_pct, s.not_desexed) == (150, 30, 83, 27)
    assert [r.suburb for r in s.outreach] == ["Kirwan", "Kelso"]


def test_od1_registrations_are_aggregated_by_suburb_and_breed():
    sheets = {
        "Dog Registrations": [
            {"Suburb": "KIRWAN ", "Desexed": "Yes", "Breed": "Kelpie"},
            {"Suburb": "Kirwan", "Desexed": "No", "Breed": "Kelpie"},
        ],
        "Cat Approvals": [{"Suburb": "Kelso", "Desexed": "Yes", "Breed": "DSH"}],
    }
    out = refresh.summarise_registrations(sheets)
    kirwan = next(s for s in out["suburbs"] if s["suburb"] == "Kirwan")
    assert (kirwan["dogs"], kirwan["dogs_desexed"], kirwan["cats"]) == (2, 1, 0)
    assert out["top_breeds"]["dog"] == [("Kelpie", 2)]


def test_od1_demo_snapshot_is_real_townsville_data():
    view = LocalAreaService(OpenData(CONFIG), _NoPractice(), TODAY).clinic_view()
    assert view["registrations"]["dogs"] > 1000 and "Kirwan" in view["registrations"]["suburbs"]


# OD-2: labels ---------------------------------------------------------------------------

BRAVECTO = Label("302", "68870", "BRAVECTO", "INTERVET", date(2027, 6, 30), {"dog": ["fleas"]})


def test_od2_product_given_to_a_species_off_its_label_is_flagged():
    check = check_label(BRAVECTO, {"dog", "cat"}, TODAY)
    assert check.current and check.off_label == ["cat"]


def test_od2_lapsed_registration_is_not_current():
    assert not check_label(BRAVECTO, {"dog"}, date(2027, 7, 1)).current


def test_od2_apvma_join_keeps_dog_and_cat_uses_of_the_clinics_products():
    products = [
        {"pcode": "1 ", "typedesc": "VM - Veterinary Medicine", "fpname": "Chew ",
         "sname": "Maker", "expdate": "30/06/2027 12:00:00 AM"},
        {"pcode": "2", "typedesc": "AC - Agricultural", "fpname": "Spray", "sname": "X",
         "expdate": "30/06/2027 12:00:00 AM"},
    ]  # fmt: skip
    uses = [
        {"pcode": "1", "hostcode": "AD6M  ", "pestcode": "UTIPA "},
        {"pcode": "1", "hostcode": "AD6M", "pestcode": "WFLA"},
        {"pcode": "1", "hostcode": "B1", "pestcode": "UTIPA"},  # not a dog or cat
        {"pcode": "2", "hostcode": "AF", "pestcode": "WFL"},  # not a vet product
    ]
    pests = [{"pestcode": "UTIPA", "pestdesc": "AUSTRALIAN PARALYSIS TICK"}]
    out = refresh.summarise_apvma(products, uses, pests, {"302": "1"})
    (label,) = out["labels"]
    assert label["product_id"] == "302" and label["expires"] == "2027-06-30"
    assert label["uses"] == {"dog": ["fleas", "paralysis tick"]}
    assert {"species": "dog", "pest": "paralysis tick", "products": 1} in out["registered"]


def test_od2_clinic_sees_its_products_with_who_they_were_dispensed_to(client):
    labels = client.get("/api/clinic/local").json()["labels"]
    chew = next(row for row in labels if row["product_id"] == "302")
    assert chew["apvma_number"] == "68870" and chew["given_to"] == ["dog"]
    assert chew["off_label"] == [] and "paralysis tick" in chew["covers"]


# OD-3: ticks ----------------------------------------------------------------------------


def test_od3_season_is_the_months_with_an_average_share_or_more():
    season = la.tick_season(SEASON, 10, TODAY)
    assert season.season == [8, 9, 10, 11, 12] and season.peak == 10 and season.in_season


def test_od3_out_of_season_in_february():
    assert not la.tick_season(SEASON, 10, date(2026, 2, 1)).in_season


def test_od3_ala_month_facets_become_counts():
    state = {"facetResults": [{"fieldName": "month", "fieldResult": [
        {"label": "October", "count": 137}, {"label": "Not supplied", "count": 29}]}]}  # fmt: skip
    out = refresh.summarise_ticks(state, {"totalRecords": 10}, 100)
    assert out["state_by_month"]["10"] == 137 and sum(out["state_by_month"].values()) == 137
    assert out["local"] == {"radius_km": 100, "records": 10}


def test_od3_dog_and_cat_owners_see_the_tick_notice_but_not_bird_owners(client):
    def kinds(pet):
        return [n["kind"] for n in client.get(f"/api/owner/dashboard?pet={pet}").json()["nearby"]]

    assert kinds("1201") == ["ticks"] and kinds("1211") == ["ticks"] and kinds("1210") == []


# OD-4: after-hours vet ------------------------------------------------------------------

DAY_VET = la.Vet("Day Vet", -19.30, 146.73, "07 1111", False, "Mo-Fr 08:00-18:00")
FAR_ER = la.Vet("Far ER", -19.60, 146.73, "07 2222", True, "")
NEAR_247 = la.Vet("Near 24/7", -19.32, 146.76, "07 3333", False, "24/7")


def test_od4_nearest_vet_open_after_hours_is_chosen():
    vet, km = la.nearest_after_hours([DAY_VET, FAR_ER, NEAR_247], -19.30, 146.73)
    assert vet.name == "Near 24/7" and 3 < km < 5


def test_od4_no_after_hours_vet_keeps_the_clinics_own_line(tmp_path):
    write(tmp_path, "vets", {"vets": []})
    local = LocalAreaService(OpenData(CONFIG, tmp_path), _NoPractice(), TODAY)
    own = ClinicContact("07 5550 0101", "After-hours line", "07 5550 0199")
    assert local.contact(own) == own


def test_od4_owner_call_now_uses_the_mapped_24_hour_vet_with_attribution(client):
    contact = client.get("/api/owner/dashboard?pet=1201").json()["contact"]
    assert contact["emergency_name"] == "JCU Vet (24 hours)"
    assert "OpenStreetMap" in contact["emergency_source"]


def test_od4_overpass_elements_without_a_name_are_dropped():
    out = refresh.summarise_vets({"elements": [
        {"type": "node", "id": 1, "lat": -19.1, "lon": 146.8, "tags": {}},
        {"type": "way", "id": 2, "center": {"lat": -19.3, "lon": 146.7},
         "tags": {"name": "V", "phone:AU": "1300", "emergency": "yes", "opening_hours": "24/7"}},
    ]})  # fmt: skip
    assert out["vets"] == [{"name": "V", "lat": -19.3, "lon": 146.7, "phone": "1300",
                            "emergency": True, "hours": "24/7", "osm": "way/2"}]  # fmt: skip


# OD-5: heat -----------------------------------------------------------------------------


def test_od5_only_hot_days_from_today_within_a_week():
    forecast = [
        la.DayForecast(date(2026, 10, 26), 40),  # yesterday
        la.DayForecast(date(2026, 10, 28), 36),
        la.DayForecast(date(2026, 10, 29), 30),
        la.DayForecast(date(2026, 11, 5), 41),  # beyond a week
    ]
    assert [f.day.day for f in la.hot_days(forecast, TODAY)] == [28]


def test_od5_dog_owners_get_a_heat_notice_cat_owners_dont(tmp_path, practice):
    write(tmp_path, "weather", {"days": [{"day": "2026-10-28", "feels_like_max": 38.2}]})
    local = LocalAreaService(OpenData(CONFIG, tmp_path), practice, TODAY)
    assert [n["kind"] for n in local.notices(practice.pet("1201"))] == ["heat"]
    assert local.notices(practice.pet("1211")) == []


# OD-6: sources --------------------------------------------------------------------------


def test_od6_every_snapshot_names_its_publisher_and_licence(client):
    sources = client.get("/api/clinic/local").json()["sources"]
    assert {s["name"] for s in sources} == {"apvma", "registrations", "ticks", "vets", "weather"}
    assert all(s["licence"] and s["publisher"] for s in sources)


def test_od6_no_snapshots_means_no_local_data_not_an_error(tmp_path):
    view = LocalAreaService(OpenData(CONFIG, tmp_path), _NoPractice(), TODAY).clinic_view()
    assert view["registrations"] is None and view["ticks"] is None and view["labels"] == []


class _NoPractice:
    def pets(self):
        return []
