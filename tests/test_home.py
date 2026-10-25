"""Owner dashboard through the API, on the demo clinic (Biscuit, 9yo Labrador, Senior plan)."""

from datetime import date

from vetagent.agent.llm import ScriptedModel
from vetagent.api.wiring import seed_demo_home
from vetagent.integrations.ezyvet import EzyVetPracticeSystem, FileSource
from vetagent.services.home import HomeService
from vetagent.services.owner_agent import OwnerAgentService

TODAY = date(2026, 10, 27)
GOOD = {"appetite": 4, "energy": 4, "mobility": 4, "comfort": 4, "toileting": 4}


def test_ht2_dashboard_shows_demo_drop_and_checkup_becomes_proposal(client):
    board = client.get("/api/owner/dashboard").json()
    assert board["checkin"]["trend"]["dropping"] is True
    convo = client.post("/api/owner/checkup").json()
    assert convo["items"][-1]["cards"][0]["type"] == "proposal"
    assert client.get("/api/clinic/requests").json() == []


def test_ht1_checking_in_twice_in_a_week_keeps_one(client):
    client.post("/api/owner/checkins", json={"scores": GOOD})
    board = client.post("/api/owner/checkins", json={"scores": {**GOOD, "energy": 3}}).json()
    assert board["checkin"]["done_this_week"] is True
    assert board["checkin"]["latest"]["energy"] == 3
    assert [h["week"] for h in board["checkin"]["history"]].count("2026-W44") == 1


def test_ht1_invalid_check_in_is_rejected(client):
    assert client.post("/api/owner/checkins", json={"scores": {"energy": 9}}).status_code == 400


def test_ht3_clinic_sees_trend_only_when_owner_shares(client):
    def biscuit_note():
        rows = client.get("/api/clinic/care-gaps").json()
        return next(r["home_note"] for r in rows if r["pet"] == "Biscuit")

    assert biscuit_note() == "Home check-ins: mobility down"
    client.put("/api/owner/consent", json={"share_log": False, "deidentified_use": False})
    assert biscuit_note() is None


def test_ht4_member_forecast_compares_plan_with_pay_as_you_go(client):
    plan = client.get("/api/owner/dashboard").json()["forecast"]["plan"]
    assert plan["member"] and plan["saving"] == 944 - plan["total"]


def test_ht6_injection_cannot_be_logged_at_home(client):
    response = client.post("/api/owner/doses", json={"product": "Annual heartworm injection"})
    assert response.status_code == 400


def test_ht6_home_dose_counts_towards_cover(client):
    board = client.post("/api/owner/doses", json={"product": "3-month flea and tick chew"}).json()
    chew = next(c for c in board["cover"] if c["product"] == "3-month flea and tick chew")
    assert chew["days_left"] == 90 and chew["owner_reported"] is True


def test_br1_household_lists_every_species_the_owner_registered(client):
    assert client.get("/api/owner/household").json() == {"species": ["bird", "dog"]}


def test_ht2_checkup_twice_gets_two_distinct_tool_call_ids(practice, store):
    seed_demo_home(store)
    agent = OwnerAgentService(practice, store, ScriptedModel(), TODAY, "501", "1201")
    agent.propose_checkup()
    agent.propose_checkup()
    ids = [c["id"] for m in store.messages("501") for c in m.get("tool_calls", [])]
    assert len(ids) == len(set(ids))


def test_ht2_checkup_is_refused_when_check_ins_are_steady(client):
    # A steady check-in this week: the latest two weeks are no longer both low.
    client.post("/api/owner/checkins", json={"scores": GOOD})
    assert client.post("/api/owner/checkup").status_code == 409


def test_ht4_non_member_is_compared_with_the_plan_for_their_life_stage(practice, store):
    nala = HomeService(practice, store, TODAY, "507", "1207")  # 7yo retriever, no plan
    plan = nala.dashboard()["forecast"]["plan"]
    assert (plan["name"], plan["member"]) == ("Adult", False)


class _RetiredSeniorPlan(FileSource):
    def list(self, endpoint: str) -> list[dict]:
        records = super().list(endpoint)
        if endpoint == "v2/wellnessplan":
            return [{**r, "active": r["name"] != "Senior"} for r in records]
        return records


def test_ht4_membership_on_a_retired_plan_is_not_counted():
    practice = EzyVetPracticeSystem(_RetiredSeniorPlan())
    assert "1201" not in {m.pet_id for m in practice.memberships()}
