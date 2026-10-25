"""Owner app through the API, on the demo household: Biscuit (9yo Labrador, Senior plan),
Mango (cockatiel) and Pip (9-week-old kitten)."""

from datetime import date

from vetagent.agent.llm import ScriptedModel
from vetagent.api.wiring import seed_demo_home
from vetagent.integrations.ezyvet import EzyVetPracticeSystem, FileSource
from vetagent.services.home import HomeService
from vetagent.services.owner_agent import OwnerAgentService

TODAY = date(2026, 10, 27)
GOOD = {"appetite": 4, "energy": 4, "mobility": 4, "comfort": 4, "toileting": 4}
BISCUIT, MANGO, PIP = "1201", "1210", "1211"
VOMITING_2_DAYS = {"symptom": "vomiting", "hours": 48, "eating": True, "bright": True}


def board(client, pet=BISCUIT):
    return client.get(f"/api/owner/dashboard?pet={pet}").json()


# Costs (CO) --------------------------------------------------------------------------


def test_co1_open_estimate_is_shown_line_by_line(client):
    (estimate,) = board(client)["costs"]["estimates"]
    assert estimate["vet"] == "Dr Lee"
    assert [line["optional"] for line in estimate["lines"]] == [False, False, True, True]
    assert all(line["explanation"] for line in estimate["lines"])


def test_co2_plan_included_lines_cost_the_owner_nothing(client):
    (estimate,) = board(client)["costs"]["estimates"]
    assert estimate["included"] == 280
    assert estimate["recommended"] == {"low": 92, "high": 92}
    assert estimate["with_optional"] == {"low": 577, "high": 717}


def test_co3_accepting_prepares_a_reply_and_sends_nothing(client):
    body = {"choice": "accept", "optional_lines": ["Hip X-rays with sedation"]}
    convo = client.post("/api/owner/estimates/5101/reply?pet=1201", json=body).json()
    card = convo["items"][-1]["cards"][0]
    assert "Hip X-rays" in card["detail"] and "Pain-relief" not in card["detail"]
    assert client.get("/api/clinic/requests").json() == []
    client.post(f"/api/owner/proposals/{card['proposal_id']}/confirm")
    assert client.get("/api/clinic/requests").json()[0]["kind"] == "estimate_reply"


def test_co3_question_needs_text(client):
    body = {"choice": "question", "question": "  "}
    assert client.post("/api/owner/estimates/5101/reply?pet=1201", json=body).status_code == 409


def test_co3_unknown_estimate_is_rejected(client):
    body = {"choice": "cheaper"}
    assert client.post("/api/owner/estimates/999/reply?pet=1201", json=body).status_code == 400


def test_co4_year_ahead_compares_plan_with_pay_as_you_go(client):
    plan = board(client)["costs"]["year"]["plan"]
    assert plan["member"] and plan["saving"] == 944 - plan["total"]


def test_co4_non_member_is_compared_with_the_plan_for_their_life_stage(practice, store):
    nala = HomeService(practice, store, TODAY, "507").dashboard("1207")  # 7yo, no plan
    assert nala["costs"]["year"]["plan"]["name"] == "Adult"


# Last visit (VR) -----------------------------------------------------------------------


def test_vr1_latest_recap_shows_progress_and_results(client):
    visit = board(client)["visit"]
    assert visit["vet"] == "Dr Lee"
    assert visit["instructions"][0]["progress"] == "Day 6 of 14"
    assert visit["results"][0]["status"] == "normal"


def test_vr2_owner_ticks_an_instruction(client):
    item = board(client)["visit"]["instructions"][0]["key"]
    after = client.post("/api/owner/ticks?pet=1201", json={"item": item, "done": True}).json()
    assert after["visit"]["instructions"][0]["done"] is True


def test_vr2_unknown_tick_is_rejected(client):
    body = {"item": "anything", "done": True}
    assert client.post("/api/owner/ticks?pet=1201", json=body).status_code == 400


def test_vr3_follow_up_and_question_become_proposals(client):
    convo = client.post("/api/owner/visits/rc-1201-1022/follow-up?pet=1201").json()
    assert convo["items"][-1]["cards"][0]["detail"] == "Recheck with Dr Lee · by 5 Nov"
    body = {"question": "Can he swim?"}
    convo = client.post("/api/owner/visits/rc-1201-1022/question?pet=1201", json=body).json()
    assert "About the visit on 22 Oct: Can he swim?" in convo["items"][-1]["cards"][0]["detail"]


# Should I come in? (TR) ----------------------------------------------------------------


def test_tr1_routes_and_logs_the_answer(client, store):
    result = client.post("/api/owner/triage?pet=1201", json=VOMITING_2_DAYS).json()
    assert result["level"] == "within_24h"


def test_tr2_red_flag_is_call_now_with_both_numbers(client):
    body = {**VOMITING_2_DAYS, "symptom": "tick", "hours": 3}
    assert client.post("/api/owner/triage?pet=1201", json=body).json()["level"] == "call_now"
    contact = board(client)["contact"]
    assert contact["phone"] and contact["emergency_phone"]


def test_tr3_within_24h_prepares_tomorrows_booking(client):
    convo = client.post("/api/owner/triage/request?pet=1201", json=VOMITING_2_DAYS).json()
    assert "first appointment tomorrow" in convo["items"][-1]["cards"][0]["detail"]


def test_tr3_call_now_never_becomes_a_proposal(client):
    body = {**VOMITING_2_DAYS, "symptom": "seizure"}
    assert client.post("/api/owner/triage/request?pet=1201", json=body).status_code == 409


def test_co4_plans_for_dogs_and_cats_are_not_offered_for_a_bird(client):
    assert board(client, MANGO)["costs"]["year"]["plan"] is None


def test_tr4_birds_are_told_to_call(client):
    assert board(client, MANGO)["triage"]["available"] is False
    assert client.post("/api/owner/triage?pet=1210", json=VOMITING_2_DAYS).status_code == 400


def test_tr5_answers_are_logged(practice, store):
    home = HomeService(practice, store, TODAY, "501")
    home.triage(BISCUIT, "skin", 96, True, True)
    assert store.triage_log(BISCUIT) == [{"symptom": "skin", "hours": 96, "level": "watch"}]


# First 90 days (NP) --------------------------------------------------------------------


def test_np1_kitten_gets_the_pathway_and_seniors_do_not(client):
    pip, biscuit = board(client, PIP), board(client)
    assert biscuit["pathway"] is None
    vaccines = [s for s in pip["pathway"]["steps"] if s["key"].startswith("vaccine")]
    assert [(s["done"], s["when"]) for s in vaccines] == [
        (True, ""),
        (False, "from 12 Nov"),
        (False, "from 10 Dec"),
    ]


def test_np1_home_steps_are_ticked_by_the_owner(client):
    after = client.post(
        "/api/owner/ticks?pet=1211", json={"item": "microchip", "done": True}
    ).json()
    step = next(s for s in after["pathway"]["steps"] if s["key"] == "microchip")
    assert step["done"] is True


def test_np1_non_member_kitten_sees_the_young_plan(client):
    assert board(client, PIP)["pathway"]["plan_offer"]["name"] == "Puppy and Kitten"


# Weekly check-in for seniors (HT) ------------------------------------------------------


def test_ht1_check_in_shows_for_senior_pets_only(client):
    assert board(client)["checkin"] is not None
    assert board(client, PIP)["checkin"] is None


def test_ht1_checking_in_twice_in_a_week_keeps_one(client):
    client.post("/api/owner/checkins?pet=1201", json={"scores": GOOD})
    body = {"scores": {**GOOD, "energy": 3}}
    after = client.post("/api/owner/checkins?pet=1201", json=body).json()["checkin"]
    assert after["done_this_week"] and after["latest"]["energy"] == 3
    assert [h["week"] for h in after["history"]].count("2026-W44") == 1


def test_ht1_invalid_check_in_is_rejected(client):
    body = {"scores": {"energy": 9}}
    assert client.post("/api/owner/checkins?pet=1201", json=body).status_code == 400


def test_ht2_demo_drop_offers_a_check_up(client):
    assert board(client)["checkin"]["trend"]["dropping"] is True
    convo = client.post("/api/owner/checkup?pet=1201").json()
    assert convo["items"][-1]["cards"][0]["type"] == "proposal"


def test_ht2_check_up_is_refused_when_steady(client):
    client.post("/api/owner/checkins?pet=1201", json={"scores": GOOD})
    assert client.post("/api/owner/checkup?pet=1201").status_code == 409


def test_ht2_repeated_proposals_get_distinct_tool_call_ids(practice, store):
    seed_demo_home(store)
    agent = OwnerAgentService(practice, store, ScriptedModel(), TODAY, "501")
    agent.propose_checkup(BISCUIT)
    agent.propose_checkup(BISCUIT)
    ids = [c["id"] for m in store.messages(f"501:{BISCUIT}") for c in m.get("tool_calls", [])]
    assert len(ids) == len(set(ids))


def test_ht3_clinic_sees_trend_only_when_owner_shares(client):
    def biscuit_note():
        rows = client.get("/api/clinic/care-gaps").json()
        return next(r["home_note"] for r in rows if r["pet"] == "Biscuit")

    assert biscuit_note() == "Home check-ins: mobility down"
    body = {"share_log": False, "deidentified_use": False}
    client.put("/api/owner/consent?pet=1201", json=body)
    assert biscuit_note() is None


class _RetiredSeniorPlan(FileSource):
    def list(self, endpoint: str) -> list[dict]:
        records = super().list(endpoint)
        if endpoint == "v2/wellnessplan":
            return [{**r, "active": r["name"] != "Senior"} for r in records]
        return records


def test_ht4_membership_on_a_retired_plan_is_not_counted():
    practice = EzyVetPracticeSystem(_RetiredSeniorPlan())
    assert BISCUIT not in {m.pet_id for m in practice.memberships()}
