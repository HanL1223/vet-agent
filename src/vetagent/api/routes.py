"""API routes. Each handler delegates to one service call."""

from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Request

from vetagent.api.schemas import (
    CheckInRequest,
    ConsentRequest,
    DoseRequest,
    MessageRequest,
    ReminderRequest,
)
from vetagent.api.wiring import Services
from vetagent.domain.models import GapType
from vetagent.services.home import DashboardError
from vetagent.services.owner_agent import ProposalError

clinic = APIRouter(prefix="/api/clinic", tags=["clinic"])
owner = APIRouter(prefix="/api/owner", tags=["owner"])


def _services(request: Request) -> Services:
    return request.app.state.services


# Clinic dashboard ------------------------------------------------------------


@clinic.get("/summary")
def summary(request: Request) -> dict:
    return _services(request).clinic.summary()


@clinic.get("/care-gaps")
def care_gaps(request: Request, type: str | None = None) -> list[dict]:
    if type and type not in {t.value for t in GapType}:
        raise HTTPException(400, f"Unknown gap type: {type}")
    return [asdict(row) for row in _services(request).clinic.gap_rows(type)]


@clinic.post("/reminders")
def send_reminders(request: Request, body: ReminderRequest) -> dict:
    return {"sent": _services(request).clinic.send_reminders(body.keys)}


@clinic.get("/plans")
def plans(request: Request) -> list[dict]:
    return _services(request).clinic.plans()


@clinic.get("/requests")
def requests_from_owners(request: Request) -> list[dict]:
    return _services(request).clinic.clinic_requests()


# Owner care agent --------------------------------------------------------------


@owner.get("/conversation")
def conversation(request: Request) -> dict:
    return _services(request).owner_agent.conversation()


@owner.post("/messages")
def send_message(request: Request, body: MessageRequest) -> dict:
    if not body.text.strip():
        raise HTTPException(400, "Message is empty")
    return _services(request).owner_agent.send(body.text)


@owner.post("/proposals/{proposal_id}/confirm")
def confirm(request: Request, proposal_id: str) -> dict:
    try:
        return _services(request).owner_agent.confirm(proposal_id)
    except ProposalError as exc:
        raise HTTPException(409, str(exc)) from exc


@owner.post("/proposals/{proposal_id}/dismiss")
def dismiss(request: Request, proposal_id: str) -> dict:
    try:
        return _services(request).owner_agent.dismiss(proposal_id)
    except ProposalError as exc:
        raise HTTPException(409, str(exc)) from exc


@owner.put("/consent")
def set_consent(request: Request, body: ConsentRequest) -> dict:
    return _services(request).owner_agent.set_consent(body.share_log, body.deidentified_use)


@owner.post("/checkup")
def checkup(request: Request) -> dict:
    try:
        return _services(request).owner_agent.propose_checkup()
    except ProposalError as exc:
        raise HTTPException(409, str(exc)) from exc


@owner.post("/reset")
def reset(request: Request) -> dict:
    return _services(request).owner_agent.reset()


# Owner pet dashboard -------------------------------------------------------------


@owner.get("/dashboard")
def dashboard(request: Request) -> dict:
    return _services(request).home.dashboard()


@owner.get("/household")
def household(request: Request) -> dict:
    return {"species": _services(request).home.household()}


@owner.post("/checkins")
def check_in(request: Request, body: CheckInRequest) -> dict:
    try:
        return _services(request).home.check_in(body.scores)
    except DashboardError as exc:
        raise HTTPException(400, str(exc)) from exc


@owner.post("/doses")
def log_dose(request: Request, body: DoseRequest) -> dict:
    try:
        return _services(request).home.log_dose(body.product)
    except DashboardError as exc:
        raise HTTPException(400, str(exc)) from exc
