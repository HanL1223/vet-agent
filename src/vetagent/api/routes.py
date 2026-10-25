"""API routes. Each handler delegates to one service call."""

from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Request

from vetagent.api.schemas import (
    CheckInRequest,
    ConsentRequest,
    EstimateReply,
    MessageRequest,
    QuestionRequest,
    RecapDraft,
    ReminderRequest,
    SendEstimate,
    TickRequest,
    TriageRequest,
)
from vetagent.api.wiring import Services
from vetagent.domain.models import GapType
from vetagent.services.clinic import ClinicError
from vetagent.services.home import DashboardError, PetNotFound
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


@clinic.get("/estimates")
def clinic_estimates(request: Request) -> list[dict]:
    return _services(request).clinic.estimates()


@clinic.post("/estimates/{estimate_id}/send")
def send_estimate(request: Request, estimate_id: str, body: SendEstimate) -> dict:
    return _clinic(lambda c: c.send_estimate(estimate_id, body.explanations), request)


@clinic.get("/recaps")
def clinic_recaps(request: Request) -> dict:
    clinic_service = _services(request).clinic
    return {"recaps": clinic_service.recaps(), **clinic_service.recap_options()}


@clinic.post("/recaps")
def write_recap(request: Request, body: RecapDraft) -> dict:
    draft = body.model_dump(exclude={"pet_id"})
    return _clinic(lambda c: c.write_recap(body.pet_id, draft), request)


def _clinic(call, request: Request):
    try:
        return call(_services(request).clinic)
    except ClinicError as exc:
        raise HTTPException(400, str(exc)) from exc


# Owner app: every call names the pet, and only the owner's own pets are allowed (OW-1) ----


def _pet(request: Request, pet: str) -> str:
    try:
        return _services(request).home.pet(pet).id
    except PetNotFound as exc:
        raise HTTPException(404, "Pet not found") from exc


@owner.get("/pets")
def pets(request: Request) -> list[dict]:
    return _services(request).home.pets()


@owner.get("/dashboard")
def dashboard(request: Request, pet: str) -> dict:
    return _services(request).home.dashboard(_pet(request, pet))


@owner.get("/conversation")
def conversation(request: Request, pet: str) -> dict:
    return _services(request).owner_agent.conversation(_pet(request, pet))


@owner.post("/messages")
def send_message(request: Request, pet: str, body: MessageRequest) -> dict:
    if not body.text.strip():
        raise HTTPException(400, "Message is empty")
    return _services(request).owner_agent.send(_pet(request, pet), body.text)


@owner.post("/proposals/{proposal_id}/confirm")
def confirm(request: Request, proposal_id: str) -> dict:
    return _proposal(lambda agent: agent.confirm(proposal_id), request)


@owner.post("/proposals/{proposal_id}/dismiss")
def dismiss(request: Request, proposal_id: str) -> dict:
    return _proposal(lambda agent: agent.dismiss(proposal_id), request)


@owner.put("/consent")
def set_consent(request: Request, pet: str, body: ConsentRequest) -> dict:
    agent = _services(request).owner_agent
    return agent.set_consent(_pet(request, pet), body.share_log, body.deidentified_use)


@owner.post("/reset")
def reset(request: Request, pet: str) -> dict:
    return _services(request).owner_agent.reset(_pet(request, pet))


@owner.post("/checkins")
def check_in(request: Request, pet: str, body: CheckInRequest) -> dict:
    return _dashboard(lambda home: home.check_in(_pet(request, pet), body.scores), request)


@owner.post("/checkup")
def checkup(request: Request, pet: str) -> dict:
    pet_id = _pet(request, pet)
    return _proposal(lambda agent: agent.propose_checkup(pet_id), request)


@owner.post("/triage")
def triage(request: Request, pet: str, body: TriageRequest) -> dict:
    pet_id = _pet(request, pet)
    return _dashboard(
        lambda home: home.triage(pet_id, body.symptom, body.hours, body.eating, body.bright),
        request,
    )


@owner.post("/triage/request")
def triage_request(request: Request, pet: str, body: TriageRequest) -> dict:
    """TR-3: the outcome is worked out again here, never trusted from the page."""
    pet_id = _pet(request, pet)
    result = _dashboard(
        lambda home: home.triage(pet_id, body.symptom, body.hours, body.eating, body.bright),
        request,
    )
    return _proposal(
        lambda agent: agent.propose_from_triage(
            pet_id, result["level"], result["symptom"], result["duration"]
        ),
        request,
    )


@owner.post("/estimates/{estimate_id}/reply")
def estimate_reply(request: Request, pet: str, estimate_id: str, body: EstimateReply) -> dict:
    pet_id = _pet(request, pet)
    _dashboard(lambda home: home.estimate(pet_id, estimate_id), request)
    return _proposal(
        lambda agent: agent.propose_estimate_reply(
            pet_id, estimate_id, body.choice, body.optional_lines, body.question
        ),
        request,
    )


@owner.post("/ticks")
def tick(request: Request, pet: str, body: TickRequest) -> dict:
    return _dashboard(lambda home: home.tick(_pet(request, pet), body.item, body.done), request)


@owner.post("/visits/{recap_id}/follow-up")
def visit_follow_up(request: Request, pet: str, recap_id: str) -> dict:
    pet_id = _pet(request, pet)
    recap = _dashboard(lambda home: home.recap(pet_id, recap_id), request)
    when = f"by {recap.follow_up_by.day} {recap.follow_up_by:%b}" if recap.follow_up_by else ""
    return _proposal(lambda agent: agent.propose_follow_up(pet_id, recap.follow_up, when), request)


@owner.post("/visits/{recap_id}/question")
def visit_question(request: Request, pet: str, recap_id: str, body: QuestionRequest) -> dict:
    pet_id = _pet(request, pet)
    recap = _dashboard(lambda home: home.recap(pet_id, recap_id), request)
    visit = f"{recap.visit.day} {recap.visit:%b}"
    return _proposal(
        lambda agent: agent.propose_visit_question(pet_id, visit, body.question), request
    )


def _dashboard(call, request: Request):
    try:
        return call(_services(request).home)
    except DashboardError as exc:
        raise HTTPException(400, str(exc)) from exc


def _proposal(call, request: Request):
    try:
        return call(_services(request).owner_agent)
    except ProposalError as exc:
        raise HTTPException(409, str(exc)) from exc
