"""Builds the app's dependencies in one place. Swap an adapter here, nowhere else."""

from dataclasses import dataclass

from vetagent.agent.llm import ClaudeModel, Model, ScriptedModel
from vetagent.config import Settings
from vetagent.integrations.practice import PracticeSystem, SeedPracticeSystem
from vetagent.services.clinic import ClinicService
from vetagent.services.owner_agent import OwnerAgentService
from vetagent.store.sqlite import Store

# The demo signs in as one owner with one pet. Real auth replaces these.
DEMO_OWNER_ID = "o1"
DEMO_PET_ID = "p1"


@dataclass(frozen=True)
class Services:
    clinic: ClinicService
    owner_agent: OwnerAgentService


def build_services(
    settings: Settings,
    practice: PracticeSystem | None = None,
    model: Model | None = None,
) -> Services:
    practice = practice or SeedPracticeSystem()
    store = Store(settings.db_path)
    if model is None:
        model = (
            ClaudeModel(settings.anthropic_api_key, settings.model)
            if settings.use_claude
            else ScriptedModel()
        )
    return Services(
        clinic=ClinicService(practice, store, settings.today),
        owner_agent=OwnerAgentService(
            practice, store, model, settings.today, DEMO_OWNER_ID, DEMO_PET_ID
        ),
    )
