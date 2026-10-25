"""Pure rules behind the owner dashboard: check-in trend, cover and the cost forecast."""

from datetime import date, timedelta

import pytest

from vetagent.domain import checkins as ci
from vetagent.domain.care_gaps import Due, life_stage
from vetagent.domain.cover import Dose, cover
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


def test_ht5_cover_counts_days_protected_in_the_last_year():
    (result,) = cover([Dose("Chew", date(2026, 7, 29), 90)], TODAY)
    assert (result.covered_days, result.days_left) == (90, 0)


def test_ht5_dose_before_the_window_only_counts_its_overlap():
    (result,) = cover([Dose("Shot", date(2025, 6, 1), 365)], TODAY)
    assert result.covered_days == (date(2026, 6, 1) - (TODAY - timedelta(days=365))).days


def test_ht6_owner_dose_extends_cover_and_is_marked():
    doses = [Dose("Chew", date(2026, 7, 29), 90), Dose("Chew", TODAY, 90, owner_reported=True)]
    (result,) = cover(doses, TODAY)
    assert result.days_left == 90 and result.owner_reported


def test_ht6_future_dated_dose_is_ignored():
    doses = [Dose("Chew", date(2026, 7, 29), 90), Dose("Chew", date(2026, 12, 1), 90, True)]
    (result,) = cover(doses, TODAY)
    assert result.last_given == date(2026, 7, 29) and not result.owner_reported
