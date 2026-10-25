"""Builds the app's dependencies in one place. Swap an adapter here, nowhere else."""

import json
from dataclasses import dataclass
from pathlib import Path

from vetagent.agent.llm import ClaudeModel, Model, OpenAIModel, ScriptedModel
from vetagent.config import Settings
from vetagent.integrations.ezyvet import EzyVetPracticeSystem, load_config
from vetagent.integrations.open_data import OpenData
from vetagent.integrations.practice import PracticeSystem
from vetagent.services.clinic import ClinicService
from vetagent.services.home import HomeService
from vetagent.services.local_area import LocalAreaService
from vetagent.services.owner_agent import OwnerAgentService
from vetagent.store.sqlite import Store

# The demo signs in as one owner (Priya: Biscuit, Mango and Pip). Real auth replaces this.
# ezyVet contact and animal IDs from data/ezyvet/.
DEMO_OWNER_ID = "501"
# App-owned demo data (check-ins, a released recap, a sent estimate) so the app has a story.
DEMO_HOME = Path(__file__).resolve().parent.parent / "data" / "demo_home.json"


@dataclass(frozen=True)
class Services:
    clinic: ClinicService
    owner_agent: OwnerAgentService
    home: HomeService
    local: LocalAreaService


def build_services(
    settings: Settings,
    practice: PracticeSystem | None = None,
    model: Model | None = None,
) -> Services:
    practice = practice or EzyVetPracticeSystem()
    store = Store(settings.db_path)
    seed_demo_home(store)
    model = model or choose_model(settings)
    local = LocalAreaService(OpenData(load_config()), practice, settings.today)
    return Services(
        clinic=ClinicService(practice, store, settings.today),
        owner_agent=OwnerAgentService(practice, store, model, settings.today, DEMO_OWNER_ID),
        home=HomeService(practice, store, settings.today, DEMO_OWNER_ID, local),
        local=local,
    )


def seed_demo_home(store: Store, path: Path = DEMO_HOME) -> None:
    """Load demo app data once; a pet that already has its own data is left alone."""
    demo = json.loads(path.read_text(encoding="utf-8"))
    for pet_id, weeks in demo["checkins"].items():
        if not store.checkins(pet_id):
            for week in weeks:
                store.save_checkin(pet_id, week["week"], week["scores"])
    for pet_id, recaps in demo["recaps"].items():
        if not store.recaps(pet_id):
            for recap in recaps:
                store.release_recap(recap["id"], pet_id, recap)
    released = store.estimate_releases()
    for estimate_id, sent in demo["estimate_releases"].items():
        if estimate_id not in released:
            store.release_estimate(estimate_id, sent["pet_id"], sent["explanations"])


def choose_model(settings: Settings) -> Model:
    if not settings.api_key:
        return ScriptedModel()
    if settings.provider == "openai":
        return OpenAIModel(settings.api_key, settings.model)
    return ClaudeModel(settings.api_key, settings.model)
