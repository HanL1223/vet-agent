"""Pure rules behind the owner app: check-ins, forecast, estimates, triage, pathway, recaps."""

from datetime import date, timedelta

import pytest

from vetagent.domain import checkins as ci
from vetagent.domain import pathway, recaps
from vetagent.domain import triage as tr
from vetagent.domain.care_gaps import Due, life_stage
from vetagent.domain.estimates import Estimate, EstimateLine, open_estimates, owner_price
from vetagent.domain.forecast import forecast
from vetagent.domain.models import GapType, Pet, Plan

TODAY = date(2026, 10, 27)  # ISO week 2026-W44
GOOD = {"appetite": 4, "energy": 4, "mobility": 4, "comfort": 4, "toileting": 4}


def _weeks(mobility: list[int | None], last: date = TODAY - timedelta(weeks=1)) -> list:
    """One check-in per calendar week, ending at `last`; None skips a week."""
    start = last - timedelta(weeks=len(mobility) - 1)
    return [
        ci.CheckIn(ci.iso_week(start + timedelta(weeks=i)), {**GOOD, "mobility": m})
        for i, m in enumerate(mobility)
        if m is not None
    ]


def test_ht1_rejects_missing_out_of_range_or_boolean_answers():
    for bad in ({**GOOD, "mobility": 5}, {"appetite": 4}, {**GOOD, "energy": True}):
        with pytest.raises(ValueError):
            ci.validate(bad)


def test_ht1_iso_week():
    assert ci.iso_week(TODAY) == "2026-W44"


def test_ht2_two_low_weeks_after_a_steady_baseline_is_a_drop():
    trend = ci.trend(_weeks([4, 4, 4, 4, 2, 2]), TODAY)
    assert (trend.dropping, trend.measure) == (True, "mobility")


def test_ht2_one_low_week_is_not_a_drop():
    assert ci.trend(_weeks([4, 4, 4, 4, 4, 2]), TODAY).dropping is False


def test_ht2_a_missed_recent_week_means_no_trend():
    assert ci.trend(_weeks([4, 4, 4, 4, 2, None]), TODAY).dropping is False


def test_ht2_old_check_ins_do_not_count_as_recent():
    stale = _weeks([4, 4, 4, 4, 2, 2], last=TODAY - timedelta(weeks=10))
    assert ci.trend(stale, TODAY).dropping is False


def test_ht2_trend_spans_a_year_boundary():
    last = date(2027, 1, 5)  # 2027-W01
    trend = ci.trend(_weeks([4, 4, 4, 4, 2, 2], last=last), last + timedelta(weeks=1))
    assert trend.dropping is True


def test_ht2_overall_drop_without_a_mobility_drop():
    low = {**GOOD, "appetite": 2, "energy": 2}
    checkins = [
        ci.CheckIn(ci.iso_week(TODAY - timedelta(weeks=n)), low if n <= 2 else GOOD)
        for n in range(6, 0, -1)
    ]
    trend = ci.trend(checkins, TODAY)
    assert (trend.dropping, trend.measure) == (True, "overall")


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


def test_ht4_life_stage_picks_which_plans_a_pet_can_join():
    pet = Pet("x", "Rex", "dog", "Kelpie", date(2019, 1, 1), "o")
    assert life_stage(pet, TODAY) == "adult"
    assert life_stage(pet, date(2027, 1, 2)) == "senior"


def _estimate(expires: date = date(2026, 11, 21)) -> Estimate:
    return Estimate(
        "e1",
        "p",
        "Screen",
        "Dr Lee",
        date(2026, 10, 22),
        expires,
        [
            EstimateLine("Consult", "", 92, 92, False, None),
            EstimateLine("Bloods", "", 280, 280, False, "senior"),
            EstimateLine("X-rays", "", 420, 560, True, None),
        ],
    )


def test_co2_plan_included_lines_drop_out_of_what_the_owner_pays():
    price = owner_price(_estimate(), Plan("p", "Senior", 59, covers=["senior"]))
    assert (price.recommended.low, price.with_optional.high, price.included) == (92, 652, 280)


def test_co2_without_a_plan_everything_is_payable():
    price = owner_price(_estimate(), None)
    assert (price.recommended.low, price.with_optional.low, price.included) == (372, 792, 0)


def test_co1_expired_estimates_are_not_open():
    assert open_estimates([_estimate(expires=date(2026, 10, 1))], TODAY) == []


def test_tr2_every_red_flag_calls_now_whatever_else_is_true():
    for symptom in (s for s in tr.SYMPTOMS if s.red_flag):
        assert tr.route(symptom.key, 3, True, True).level is tr.Level.CALL_NOW


def test_tr1_not_bright_and_not_eating_calls_now():
    assert tr.route("skin", 3, eating_normally=False, bright=False).level is tr.Level.CALL_NOW


def test_tr1_duration_turns_watch_into_within_24h():
    assert tr.route("vomiting", 12, True, True).level is tr.Level.WATCH
    assert tr.route("vomiting", 48, True, True).level is tr.Level.WITHIN_24H


def test_tr1_only_ever_says_where_to_go_never_what_it_is():
    outcomes = {
        tr.route(key, hours, eating, bright).headline
        for key in tr.BY_KEY
        for hours, _ in tr.DURATIONS
        for eating in (True, False)
        for bright in (True, False)
    }
    assert outcomes == {"Call now", "See a vet within 24 hours", "Keep an eye on it"}


def test_tr1_unknown_input_is_rejected():
    with pytest.raises(ValueError):
        tr.route("sneezing", 3, True, True)
    with pytest.raises(ValueError):
        tr.route("vomiting", 7, True, True)


def _kitten(born: date = date(2026, 8, 20)) -> Pet:
    return Pet("k", "Pip", "cat", "DSH", born, "o")


def test_np1_course_runs_every_4_weeks_until_16_weeks():
    steps = pathway.vaccine_steps(_kitten(), [date(2026, 10, 15)], TODAY)
    assert [s.when for s in steps] == ["", "from 12 Nov", "from 10 Dec"]


def test_np1_course_is_done_after_a_dose_at_16_weeks():
    doses = [date(2026, 10, 15), date(2026, 11, 12), date(2026, 12, 10)]
    steps = pathway.vaccine_steps(_kitten(), doses, date(2026, 12, 11))
    assert all(s.done for s in steps) and len(steps) == 3


def test_np1_pathway_is_for_pets_under_six_months():
    assert pathway.is_young(_kitten(), TODAY)
    assert not pathway.is_young(_kitten(born=date(2026, 1, 1)), TODAY)


def test_np2_tip_matches_the_pets_age():
    assert "litter tray" in pathway.tip(_kitten(), TODAY)


def test_vr1_progress_counts_days_from_the_visit():
    step = recaps.Instruction("Lead walks", days=14)
    assert recaps.progress(step, date(2026, 10, 22), TODAY) == "Day 6 of 14"
    assert recaps.progress(step, date(2026, 10, 1), TODAY) == "Finished"
    assert recaps.progress(recaps.Instruction("Check in"), date(2026, 10, 22), TODAY) == ""


def test_vr1_old_recaps_drop_off():
    old = recaps.Recap("r", "p", date(2026, 6, 1), "Dr Lee", "", [], [], "", None)
    assert recaps.latest([old], TODAY) is None
