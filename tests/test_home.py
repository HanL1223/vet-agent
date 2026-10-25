from datetime import date

import pytest

from vetagent.domain import checkins as ci
from vetagent.domain.care_gaps import Due
from vetagent.domain.cover import Dose, cover
from vetagent.domain.forecast import forecast
from vetagent.domain.models import GapType, Plan

TODAY = date(2026, 10, 27)
GOOD = {"appetite": 4, "energy": 4, "mobility": 4, "comfort": 4, "toileting": 4}


def _weeks(*mobility: int) -> list[ci.CheckIn]:
    return [ci.CheckIn(f"2026-W{30 + i}", {**GOOD, "mobility": m}) for i, m in enumerate(mobility)]


def test_ht1_rejects_missing_or_out_of_range_answers():
    with pytest.raises(ValueError):
        ci.validate({**GOOD, "mobility": 5})
    with pytest.raises(ValueError):
        ci.validate({"appetite": 4})


def test_ht1_iso_week():
    assert ci.iso_week(TODAY) == "2026-W44"


def test_ht2_two_low_weeks_after_a_steady_baseline_is_a_drop():
    trend = ci.trend(_weeks(4, 4, 4, 4, 2, 2))
    assert (trend.dropping, trend.measure) == (True, "mobility")


def test_ht2_one_low_week_is_not_a_drop():
    assert ci.trend(_weeks(4, 4, 4, 4, 4, 2)).dropping is False


def test_ht2_needs_six_weeks_of_history():
    assert ci.trend(_weeks(4, 2, 2)).dropping is False


def test_ht4_overdue_care_lands_this_month_and_repeats():
    dues = [Due(GapType.PARASITE, "Chew due", "", date(2026, 10, 1), 96, every_days=90)]
    result = forecast(dues, TODAY)
    assert [i.due for i in result.items][:2] == [TODAY, date(2027, 1, 25)]
    assert result.items[0].overdue and result.pay_as_you_go == 96 * 5


def test_ht4_plan_total_counts_fees_and_care_it_does_not_include():
    dues = [
        Due(GapType.SENIOR, "Screening", "", date(2026, 12, 1), 280),
        Due(GapType.DENTAL, "Dental", "", date(2026, 12, 1), 650),
    ]
    cost = forecast(dues, TODAY).on_plan(Plan("p", "Senior", 59, covers=["senior"]))
    assert (cost.fees, cost.extras, cost.total) == (708, 650, 1358)


def test_ht5_cover_counts_days_protected_in_the_last_year():
    doses = [Dose("Chew", date(2026, 7, 29), 90)]
    (result,) = cover(doses, TODAY)
    assert (result.covered_days, result.days_left) == (90, 0)


def test_ht6_owner_dose_extends_cover_and_is_marked():
    doses = [Dose("Chew", date(2026, 7, 29), 90), Dose("Chew", TODAY, 90, owner_reported=True)]
    (result,) = cover(doses, TODAY)
    assert result.days_left == 90 and result.owner_reported


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


def test_br1_household_lists_the_owners_pet_species(client):
    assert client.get("/api/owner/household").json() == {"species": ["dog"]}
