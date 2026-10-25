"""Clinic side of estimates and visit recaps (CL-7, CL-8), and what owners then see."""

import sqlite3
from datetime import date

import pytest

from vetagent.domain import recaps
from vetagent.services.clinic import ClinicError, ClinicService
from vetagent.services.home import HomeService
from vetagent.store.sqlite import Store

TODAY = date(2026, 10, 27)
BISCUIT = "1201"
DRAFT = {
    "pet_id": BISCUIT,
    "visit": "2026-10-27",
    "vet": "Dr Lee",
    "summary": "Bloods taken today. Results by Thursday.",
    "instructions": [{"text": "Lead walks only", "days": 7}, {"text": "Keep checking in"}],
    "results": [{"name": "Bloods", "status": "follow_up", "comment": "Kidney value a bit high."}],
    "follow_up": "Recheck bloods",
    "follow_up_by": "2026-11-24",
}


# CL-7: estimates ------------------------------------------------------------------------


def test_cl7_demo_estimate_shows_as_sent(client):
    (row,) = client.get("/api/clinic/estimates").json()
    assert (row["pet"], row["status"], row["low"], row["high"]) == ("Biscuit", "sent", 857, 997)


def test_cl7_owner_sees_an_estimate_only_after_the_clinic_sends_it(practice):
    store = Store(":memory:")
    home = HomeService(practice, store, TODAY, "501")
    assert home.dashboard(BISCUIT)["costs"]["estimates"] == []
    clinic = ClinicService(practice, store, TODAY)
    assert clinic.estimates()[0]["status"] == "not_sent"
    clinic.send_estimate("5101", ["Recheck", "Bloods", "X-rays, if you'd like", "Trial"])
    (shown,) = home.dashboard(BISCUIT)["costs"]["estimates"]
    assert shown["lines"][2]["explanation"] == "X-rays, if you'd like"


def test_cl7_wording_needs_one_explanation_per_line(client):
    body = {"explanations": ["only one"]}
    assert client.post("/api/clinic/estimates/5101/send", json=body).status_code == 400


def test_cl7_unknown_estimate_is_refused(client):
    body = {"explanations": []}
    assert client.post("/api/clinic/estimates/999/send", json=body).status_code == 400


def test_cl7_owner_reply_shows_on_the_clinic_list(client):
    convo = client.post(
        "/api/owner/estimates/5101/reply?pet=1201", json={"choice": "cheaper"}
    ).json()
    client.post(f"/api/owner/proposals/{convo['items'][-1]['cards'][0]['proposal_id']}/confirm")
    (row,) = client.get("/api/clinic/estimates").json()
    assert row["status"] == "replied" and "lower-cost" in row["reply"]


# CL-8: visit recaps ---------------------------------------------------------------------


def test_cl8_recap_written_by_the_clinic_reaches_the_owner(client):
    assert client.post("/api/clinic/recaps", json=DRAFT).status_code == 200
    visit = client.get("/api/owner/dashboard?pet=1201").json()["visit"]
    assert visit["summary"] == DRAFT["summary"]
    assert visit["instructions"][0]["progress"] == "Day 1 of 7"
    assert visit["results"][0]["status"] == "follow_up"


def test_cl8_clinic_lists_recaps_newest_first_with_form_options(client):
    client.post("/api/clinic/recaps", json=DRAFT)
    body = client.get("/api/clinic/recaps").json()
    assert body["recaps"][0]["summary"] == DRAFT["summary"]
    assert "Dr Lee" in body["vets"] and any(p["name"] == "Pip" for p in body["patients"])


@pytest.mark.parametrize(
    "change",
    [
        {"visit": "2026-10-28"},  # future
        {"visit": "2026-07-01"},  # older than owners can see
        {"summary": "   "},
        {"instructions": [{"text": "Rest", "days": 0}]},
        {"results": [{"name": "Bloods", "status": "worrying", "comment": "x"}]},
        {"vet": "Dr Who"},
        {"follow_up": "", "follow_up_by": "2026-11-24"},  # a date with nothing to do
    ],
)
def test_cl8_recap_that_owners_couldnt_use_is_refused(client, change):
    assert client.post("/api/clinic/recaps", json={**DRAFT, **change}).status_code == 400


def test_cl8_recap_for_a_non_patient_is_refused(client):
    assert client.post("/api/clinic/recaps", json={**DRAFT, "pet_id": "1209"}).status_code == 400


def test_cl8_build_trims_text_and_keeps_order():
    recap = recaps.build(
        "r",
        "p",
        TODAY,
        "Dr Lee",
        "  Fine.  ",
        [recaps.Instruction(" Rest ", 3), recaps.Instruction("Walks")],
        [],
        "",
        None,
        TODAY,
    )
    assert recap.summary == "Fine." and [i.text for i in recap.instructions] == ["Rest", "Walks"]


def test_cl8_record_round_trips():
    recap = recaps.build(
        "r",
        "p",
        TODAY,
        "Dr Lee",
        "Fine",
        [recaps.Instruction("Rest", 3)],
        [recaps.Result("Bloods", "normal", "All good")],
        "Recheck",
        date(2026, 11, 3),
        TODAY,
    )
    assert recaps.from_record("p", recaps.to_record(recap)) == recap


def test_cl8_write_recap_rejects_bad_dates(practice, store):
    clinic = ClinicService(practice, store, TODAY)
    with pytest.raises(ClinicError):
        clinic.write_recap(BISCUIT, {**DRAFT, "visit": "2026-02-30"})


# Storage ----------------------------------------------------------------------------------


def test_older_database_gets_the_request_ref_column(tmp_path):
    path = tmp_path / "old.db"
    old = sqlite3.connect(path)
    old.execute(
        "CREATE TABLE clinic_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, pet_id TEXT NOT NULL,"
        " kind TEXT NOT NULL, detail TEXT NOT NULL, created_at TEXT NOT NULL)"
    )
    old.commit()
    old.close()
    store = Store(str(path))
    store.add_clinic_request("1201", "estimate_reply", "Go ahead", ref="5101")
    assert store.clinic_requests()[0]["ref"] == "5101"
