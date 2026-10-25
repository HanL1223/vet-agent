"""FastAPI app factory. Run: uvicorn vetagent.api.app:create_app --factory"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from vetagent.agent.llm import Model
from vetagent.api.routes import clinic, owner
from vetagent.api.wiring import build_services
from vetagent.config import Settings, load_settings
from vetagent.integrations.practice import PracticeSystem

WEB = Path(__file__).resolve().parent.parent / "web"


def create_app(
    settings: Settings | None = None,
    practice: PracticeSystem | None = None,
    model: Model | None = None,
) -> FastAPI:
    app = FastAPI(title="Vet care agent", version="0.1.0")
    app.state.services = build_services(settings or load_settings(), practice, model)
    app.include_router(clinic)
    app.include_router(owner)
    app.mount("/static", StaticFiles(directory=WEB), name="static")

    @app.get("/", include_in_schema=False)
    def home() -> FileResponse:
        return FileResponse(WEB / "index.html")

    @app.get("/clinic", include_in_schema=False)
    def clinic_page() -> FileResponse:
        return FileResponse(WEB / "clinic.html")

    @app.get("/owner", include_in_schema=False)
    def owner_page() -> FileResponse:
        return FileResponse(WEB / "owner.html")

    return app
