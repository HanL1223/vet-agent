"""What public Australian data says about the clinic's area (docs/requirements.md OD-*).

Pure rules over aggregated open data: council pet registrations (OD-1), paralysis tick
records (OD-3), the nearest 24-hour vet (OD-4) and hot days ahead (OD-5). The snapshots are
read in integrations/open_data.py; nothing here does I/O.
"""

from dataclasses import dataclass
from datetime import date
from math import asin, cos, radians, sin, sqrt

# Registrations --------------------------------------------------------------------------


@dataclass(frozen=True)
class SuburbPets:
    suburb: str
    dogs: int
    dogs_desexed: int
    cats: int
    cats_desexed: int

    @property
    def not_desexed(self) -> int:
        return self.dogs - self.dogs_desexed + self.cats - self.cats_desexed


@dataclass(frozen=True)
class AreaSummary:
    suburbs: list[str]
    dogs: int
    cats: int
    dogs_desexed_pct: int
    cats_desexed_pct: int
    not_desexed: int
    outreach: list[SuburbPets]  # most pets not desexed first


def area_summary(rows: list[SuburbPets], catchment: list[str], top: int = 5) -> AreaSummary:
    """OD-1: registered pets in the clinic's suburbs, and where desexing outreach reaches most."""
    wanted = {s.casefold() for s in catchment}
    local = [r for r in rows if r.suburb.casefold() in wanted]
    dogs, cats = sum(r.dogs for r in local), sum(r.cats for r in local)
    return AreaSummary(
        suburbs=sorted(r.suburb for r in local),
        dogs=dogs,
        cats=cats,
        dogs_desexed_pct=_pct(sum(r.dogs_desexed for r in local), dogs),
        cats_desexed_pct=_pct(sum(r.cats_desexed for r in local), cats),
        not_desexed=sum(r.not_desexed for r in local),
        outreach=sorted(local, key=lambda r: (-r.not_desexed, r.suburb))[:top],
    )


def _pct(part: int, whole: int) -> int:
    return round(100 * part / whole) if whole else 0


# Paralysis ticks ------------------------------------------------------------------------


@dataclass(frozen=True)
class TickSeason:
    in_season: bool
    season: list[int]  # months (1-12) with at least an average month's share of records
    peak: int
    month_share: int  # % of the state's dated records that fall in today's month
    local_records: int  # records near the clinic, any year


def tick_season(state_by_month: dict[int, int], local_records: int, today: date) -> TickSeason:
    """OD-3: is this month paralysis tick season, judged by when records are made in the state?

    Records follow people looking as much as ticks, so this is a season shape, not a risk score.
    """
    total = sum(state_by_month.values())
    mean = total / 12
    season = [m for m in range(1, 13) if total and state_by_month.get(m, 0) >= mean]
    peak = max(range(1, 13), key=lambda m: (state_by_month.get(m, 0), -m))
    return TickSeason(
        in_season=today.month in season,
        season=season,
        peak=peak,
        month_share=_pct(state_by_month.get(today.month, 0), total),
        local_records=local_records,
    )


# Nearest 24-hour vet --------------------------------------------------------------------


@dataclass(frozen=True)
class Vet:
    name: str
    lat: float
    lon: float
    phone: str
    emergency: bool
    hours: str  # OpenStreetMap opening_hours, "" when unknown

    @property
    def after_hours(self) -> bool:
        return self.emergency or self.hours.strip() == "24/7"


def km_between(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance; plenty for "which is nearest" within a city."""
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * 6371 * asin(sqrt(a))


def nearest_after_hours(vets: list[Vet], lat: float, lon: float) -> tuple[Vet, float] | None:
    """OD-4: the closest vet open 24 hours or tagged as an emergency vet, with a phone number."""
    options = [(v, km_between(lat, lon, v.lat, v.lon)) for v in vets if v.after_hours and v.phone]
    return min(options, key=lambda pair: pair[1], default=None)


# Hot days -------------------------------------------------------------------------------

# Feels-like maximum at which owners are told to walk early and keep pets cool. Each clinic's
# vets confirm the number at onboarding, as with the triage list.
HOT_FEELS_LIKE = 35.0


@dataclass(frozen=True)
class DayForecast:
    day: date
    feels_like_max: float


def hot_days(forecast: list[DayForecast], today: date, days: int = 7) -> list[DayForecast]:
    """OD-5: hot days from today on, within the forecast window. A stale forecast shows nothing."""
    return [
        f
        for f in forecast
        if 0 <= (f.day - today).days < days and f.feels_like_max >= HOT_FEELS_LIKE
    ]
