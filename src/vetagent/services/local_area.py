"""Open data about the clinic's area, for the clinic (Local area tab) and owners (Near you).

OD-1 registrations, OD-2 product labels, OD-3 tick season, OD-4 nearest 24-hour vet, OD-5 hot
days, OD-6 sources and licences. Reads snapshots only; it never fetches anything.
"""

from datetime import date

from vetagent.domain import local_area as la
from vetagent.domain.labels import check_label
from vetagent.domain.models import ClinicContact, Pet
from vetagent.integrations.open_data import OpenData
from vetagent.integrations.practice import PracticeSystem

TICK_SPECIES = ("dog", "cat")
KEY_PESTS = {"paralysis tick", "fleas", "heartworm"}
MONTH_NAMES = [date(2026, m, 1).strftime("%B") for m in range(1, 13)]


class LocalAreaService:
    def __init__(self, data: OpenData, practice: PracticeSystem, today: date) -> None:
        self._data = data
        self._practice = practice
        self._today = today

    # For the clinic ---------------------------------------------------------------------
    def clinic_view(self) -> dict:
        area = self._data.area
        nearest = self._nearest()
        return {
            "area": {"suburb": area.suburb, "state": area.state},
            "registrations": self._registrations(),
            "ticks": self._ticks(),
            "labels": self._labels(),
            "registered": self._data.registered_products(),
            "after_hours": nearest
            and {"name": nearest[0].name, "phone": nearest[0].phone, "km": round(nearest[1], 1)},
            "vets_nearby": len(self._data.vets()),
            "forecast": [
                {"day": f"{f.day:%a} {f.day.day}", "feels_like_max": f.feels_like_max}
                for f in self._data.forecast()
                if f.day >= self._today
            ],
            "hot_days": [f"{f.day:%a} {f.day.day} {f.day:%b}" for f in self._hot()],
            "hot_threshold": la.HOT_FEELS_LIKE,
            "sources": self._sources(),
        }

    def _registrations(self) -> dict | None:
        """OD-1: pets registered in the clinic's suburbs, and the desexing gap."""
        summary = la.area_summary(self._data.registrations(), self._data.area.catchment)
        if not summary.suburbs:
            return None
        return {
            "suburbs": summary.suburbs,
            "dogs": summary.dogs,
            "cats": summary.cats,
            "dogs_desexed_pct": summary.dogs_desexed_pct,
            "cats_desexed_pct": summary.cats_desexed_pct,
            "not_desexed": summary.not_desexed,
            "outreach": [
                {"suburb": s.suburb, "not_desexed": s.not_desexed, "pets": s.dogs + s.cats}
                for s in summary.outreach
            ],
            "top_breeds": self._data.top_breeds(),
        }

    def _ticks(self) -> dict | None:
        season = self._season()
        if season is None:
            return None
        return {
            "in_season": season.in_season,
            "season": _months(season.season),
            "peak": MONTH_NAMES[season.peak - 1],
            "month_share": season.month_share,
            "by_month": [
                {
                    "month": MONTH_NAMES[m - 1][:3],
                    "records": n,
                    "season": m in season.season,
                    "now": m == self._today.month,
                }
                for m, n in sorted(self._data.ticks_by_month().items())
            ],
            "local_records": season.local_records,
            "radius_km": self._data.local_ticks()["radius_km"],
        }

    # For owners -------------------------------------------------------------------------
    def contact(self, fallback: ClinicContact) -> ClinicContact:
        """OD-4: send owners to the nearest real 24-hour vet; the clinic's own line otherwise."""
        nearest = self._nearest()
        if nearest is None:
            return fallback
        vet, _ = nearest
        return ClinicContact(
            phone=fallback.phone,
            emergency_name=f"{vet.name} (24 hours)",
            emergency_phone=vet.phone,
            emergency_source="© OpenStreetMap contributors",
        )

    def notices(self, pet: Pet) -> list[dict]:
        """OD-3, OD-5: what's happening near the clinic that matters for this pet this week."""
        notices = []
        season = self._season()
        if season and season.in_season and pet.species in TICK_SPECIES:
            notices.append(
                {
                    "kind": "ticks",
                    "title": "Paralysis tick season",
                    "text": (
                        f"Most {self._data.area.state} paralysis tick records are made in "
                        f"{_months(season.season)}. Run your hands over {pet.name} every day, "
                        "and call straight away if you find a tick."
                    ),
                    "source": "Atlas of Living Australia",
                }
            )
        hot = self._hot()
        if hot and pet.species == "dog":
            days = ", ".join(f"{f.day:%A}" for f in hot[:3])
            notices.append(
                {
                    "kind": "heat",
                    "title": "Hot days ahead",
                    "text": (
                        f"It will feel {max(f.feels_like_max for f in hot):.0f}°C or hotter on "
                        f"{days}. Walk {pet.name} early or late, and leave out plenty of water."
                    ),
                    "source": "Open-Meteo",
                }
            )
        return notices

    def sources(self) -> list[dict]:
        return self._sources()

    # Helpers ------------------------------------------------------------------------
    def _season(self) -> la.TickSeason | None:
        by_month = self._data.ticks_by_month()
        if not sum(by_month.values()):
            return None
        return la.tick_season(by_month, self._data.local_ticks()["records"], self._today)

    def _nearest(self) -> tuple[la.Vet, float] | None:
        area = self._data.area
        return la.nearest_after_hours(self._data.vets(), area.lat, area.lon)

    def _hot(self) -> list[la.DayForecast]:
        return la.hot_days(self._data.forecast(), self._today)

    def _labels(self) -> list[dict]:
        """OD-2: each product's label against the species the clinic dispensed it to."""
        given: dict[str, set[str]] = {}
        sold_as: dict[str, str] = {}
        for pet in self._practice.pets():
            for event in self._practice.events(pet.id):
                if event.product_id:
                    given.setdefault(event.product_id, set()).add(pet.species)
                    sold_as[event.product_id] = event.detail
        rows = []
        for label in self._data.labels():
            check = check_label(label, given.get(label.product_id, set()), self._today)
            uses = {p for pests in label.uses.values() for p in pests}
            rows.append(
                {
                    "product_id": label.product_id,
                    "sold_as": sold_as.get(label.product_id),
                    "name": label.name,
                    "apvma_number": label.apvma_number,
                    "registrant": label.registrant,
                    "expires": label.expires.isoformat(),
                    "current": check.current,
                    "species": sorted(label.uses),
                    "covers": sorted(KEY_PESTS & uses),
                    "other_uses": len(uses - KEY_PESTS),
                    "given_to": check.given_to,
                    "off_label": check.off_label,
                }
            )
        return rows

    def _sources(self) -> list[dict]:
        return [
            {
                "name": name,
                "publisher": s.publisher,
                "licence": s.licence,
                "url": s.url,
                "fetched": s.fetched,
            }
            for name, s in self._data.sources().items()
        ]


def _months(months: list[int]) -> str:
    """[8, 9, 10, 11, 12] -> "August to December"; a broken run is listed month by month."""
    names = [MONTH_NAMES[m - 1] for m in months]
    if len(names) > 2 and months == list(range(months[0], months[-1] + 1)):
        return f"{names[0]} to {names[-1]}"
    return " and ".join([", ".join(names[:-1]), names[-1]]) if len(names) > 1 else "".join(names)
