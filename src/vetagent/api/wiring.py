"""Builds the app's dependencies in one place. Swap an adapter here, nowhere else."""

import json
from dataclasses import dataclass
from pathlib import Path

from vetagent.agent.llm import ClaudeModel, Model, OpenAIModel, ScriptedModel
from vetagent.config import Settings
from vetagent.integrations.ezyvet import EzyVetPracticeSystem
from vetagent.integrations.practice import PracticeSystem
from vetagent.services.clinic import ClinicService
from vetagent.services.home import HomeService
from vetagent.services.owner_agent import OwnerAgentService
from vetagent.store.sqlite import Store

# The demo signs in as one owner with one pet. Real auth replaces these.
# ezyVet contact and animal IDs from data/ezyvet/.
DEMO_OWNER_ID = "501"
DEMO_PET_ID = "1201"
# App-owned demo history (weekly check-ins) so the dashboard has weeks to show.
DEMO_HOME = Path(__file__).resolve().parent.parent / "data" / "demo_home.json"


@dataclass(frozen=True)
class Services:
    clinic: ClinicService
    owner_agent: OwnerAgentService
    home: HomeService


def build_services(
    settings: Settings,
    practice: PracticeSystem | None = None,
    model: Model | None = None,
) -> Services:
    practice = practice or EzyVetPracticeSystem()
    store = Store(settings.db_path)
    seed_demo_home(store)
    model = model or choose_model(settings)
    return Services(
        clinic=ClinicService(practice, store, settings.today),
        owner_agent=OwnerAgentService(
            practice, store, model, settings.today, DEMO_OWNER_ID, DEMO_PET_ID
        ),
        home=HomeService(practice, store, settings.today, DEMO_OWNER_ID, DEMO_PET_ID),
    )


def seed_demo_home(store: Store, path: Path = DEMO_HOME) -> None:
    """Load demo check-ins once; a pet that already has check-ins is left alone."""
    for pet_id, weeks in json.loads(path.read_text(encoding="utf-8")).items():
        if not store.checkins(pet_id):
            for week in weeks:
                store.save_checkin(pet_id, week["week"], week["scores"])


def choose_model(settings: Settings) -> Model:
    if not settings.api_key:
        return ScriptedModel()
    if settings.provider == "openai":
        return OpenAIModel(settings.api_key, settings.model)
    return ClaudeModel(settings.api_key, settings.model)
