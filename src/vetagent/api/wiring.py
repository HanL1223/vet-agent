"""Builds the app's dependencies in one place. Swap an adapter here, nowhere else."""

from dataclasses import dataclass

from vetagent.agent.llm import ClaudeModel, Model, OpenAIModel, ScriptedModel
from vetagent.config import Settings
from vetagent.integrations.ezyvet import EzyVetPracticeSystem
from vetagent.integrations.practice import PracticeSystem
from vetagent.services.clinic import ClinicService
from vetagent.services.owner_agent import OwnerAgentService
from vetagent.store.sqlite import Store

# The demo signs in as one owner with one pet. Real auth replaces these.
# ezyVet contact and animal IDs from data/ezyvet/.
DEMO_OWNER_ID = "501"
DEMO_PET_ID = "1201"


@dataclass(frozen=True)
class Services:
    clinic: ClinicService
    owner_agent: OwnerAgentService


def build_services(
    settings: Settings,
    practice: PracticeSystem | None = None,
    model: Model | None = None,
) -> Services:
    practice = practice or EzyVetPracticeSystem()
    store = Store(settings.db_path)
    model = model or choose_model(settings)
    return Services(
        clinic=ClinicService(practice, store, settings.today),
        owner_agent=OwnerAgentService(
            practice, store, model, settings.today, DEMO_OWNER_ID, DEMO_PET_ID
        ),
    )


def choose_model(settings: Settings) -> Model:
    if not settings.api_key:
        return ScriptedModel()
    if settings.provider == "openai":
        return OpenAIModel(settings.api_key, settings.model)
    return ClaudeModel(settings.api_key, settings.model)
