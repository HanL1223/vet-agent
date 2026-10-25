from datetime import date

import pytest
from fastapi.testclient import TestClient

from vetagent.agent.llm import ScriptedModel
from vetagent.agent.tools import ToolContext
from vetagent.api.app import create_app
from vetagent.api.wiring import DEMO_OWNER_ID, DEMO_PET_ID
from vetagent.config import Settings
from vetagent.integrations.ezyvet import EzyVetPracticeSystem
from vetagent.store.sqlite import Store

TODAY = date(2026, 10, 27)


@pytest.fixture
def practice() -> EzyVetPracticeSystem:
    return EzyVetPracticeSystem()


@pytest.fixture
def store() -> Store:
    return Store(":memory:")


@pytest.fixture
def ctx(practice, store) -> ToolContext:
    return ToolContext(DEMO_OWNER_ID, DEMO_PET_ID, practice, store, TODAY)


@pytest.fixture
def client(tmp_path) -> TestClient:
    settings = Settings(anthropic_api_key="", model="", today=TODAY, db_path=str(tmp_path / "t.db"))
    return TestClient(create_app(settings, model=ScriptedModel()))
