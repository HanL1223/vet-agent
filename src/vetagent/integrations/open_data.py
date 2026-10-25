"""Reads the open-data snapshots in data/open/ into domain records (docs/open-data.md).

The snapshots are written by `vetagent-open-data` (integrations/open_data_refresh.py). A
missing snapshot means "no data", never an error: the app works without any of them.
"""

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from vetagent.domain.labels import Label
from vetagent.domain.local_area import DayForecast, SuburbPets, Vet

OPEN_DIR = Path(__file__).resolve().parent.parent / "data" / "open"


@dataclass(frozen=True)
class Area:
    """Where the clinic is, from clinic_config.json "open_data"."""

    suburb: str
    state: str
    lat: float
    lon: float
    catchment: list[str]


@dataclass(frozen=True)
class Source:
    publisher: str
    licence: str
    url: str
    fetched: str


class OpenData:
    def __init__(self, config: dict, folder: Path = OPEN_DIR) -> None:
        settings = config["open_data"]
        self.area = Area(
            suburb=settings["suburb"],
            state=settings["state"],
            lat=settings["lat"],
            lon=settings["lon"],
            catchment=settings["catchment_suburbs"],
        )
        self._snapshots = {
            path.stem: json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(folder.glob("*.json"))
        }

    def sources(self) -> dict[str, Source]:
        """OD-6: who each snapshot came from, under which licence, and when."""
        return {
            name: Source(
                s["_source"]["publisher"],
                s["_source"]["licence"],
                s["_source"]["url"],
                s["_source"]["fetched"],
            )
            for name, s in self._snapshots.items()
        }

    def registrations(self) -> list[SuburbPets]:
        return [SuburbPets(**row) for row in self._get("registrations", "suburbs", [])]

    def top_breeds(self) -> dict[str, list[tuple[str, int]]]:
        breeds = self._get("registrations", "top_breeds", {})
        return {species: [tuple(pair) for pair in rows] for species, rows in breeds.items()}

    def labels(self) -> list[Label]:
        return [
            Label(
                product_id=row["product_id"],
                apvma_number=row["apvma_number"],
                name=row["name"],
                registrant=row["registrant"],
                expires=date.fromisoformat(row["expires"]),
                uses=row["uses"],
            )
            for row in self._get("apvma", "labels", [])
        ]

    def registered_products(self) -> list[dict]:
        return self._get("apvma", "registered", [])

    def ticks_by_month(self) -> dict[int, int]:
        return {int(m): n for m, n in self._get("ticks", "state_by_month", {}).items()}

    def local_ticks(self) -> dict:
        return self._get("ticks", "local", {"radius_km": 0, "records": 0})

    def vets(self) -> list[Vet]:
        return [
            Vet(v["name"], v["lat"], v["lon"], v["phone"], v["emergency"], v["hours"])
            for v in self._get("vets", "vets", [])
        ]

    def forecast(self) -> list[DayForecast]:
        return [
            DayForecast(date.fromisoformat(d["day"]), d["feels_like_max"])
            for d in self._get("weather", "days", [])
        ]

    def _get(self, snapshot: str, key: str, default):
        return self._snapshots.get(snapshot, {}).get(key, default)
