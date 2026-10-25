"""Owner care-agent use cases: one conversation per pet, proposals, and confirming them.

Dashboard actions (an estimate reply, a triage outcome, a recap follow-up, a check-up) land in
the same conversation as proposals, so the owner always confirms in one place (AG-4).
"""

import uuid
from datetime import date
from typing import Any

from vetagent.agent.display import to_chat_items
from vetagent.agent.llm import Model
from vetagent.agent.loop import run_turn
from vetagent.agent.prompts import system_prompt
from vetagent.agent.tools import ToolContext, run_tool
from vetagent.domain import checkins as ci
from vetagent.integrations.practice import PracticeSystem
from vetagent.store.sqlite import Consent, Store

CONFIRMED = {
    "booking_request": ("Send to clinic", "Booking requested", "the clinic will confirm by SMS"),
    "estimate_reply": ("Send to clinic", "Sent to the clinic", "they'll reply in this chat"),
    "vet_note": ("Send the note", "", "The team will reply in this chat"),
}


class ProposalError(Exception):
    pass


class OwnerAgentService:
    def __init__(
        self, practice: PracticeSystem, store: Store, model: Model, today: date, owner_id: str
    ) -> None:
        self._practice = practice
        self._store = store
        self._model = model
        self._today = today
        self._owner_id = owner_id

    # Queries -----------------------------------------------------------------
    def conversation(self, pet_id: str) -> dict:
        if not self._store.messages(self._key(pet_id)):
            self._open(pet_id)
        pet = self._practice.pet(pet_id)
        consent = self._store.consent(self._owner_id)
        return {
            "clinic": self._practice.clinic_name(),
            "pet": {"id": pet.id, "name": pet.name, "species": pet.species},
            "owner": self._first_name(),
            "model": self._model.name,
            "consent": {
                "share_log": consent.share_log,
                "deidentified_use": consent.deidentified_use,
            },
            "items": to_chat_items(self._store.messages(self._key(pet_id)), self._status),
        }

    # Commands ------------------------------------------------------------------
    def send(self, pet_id: str, text: str) -> dict:
        history = self._store.messages(self._key(pet_id))
        system = self._system(pet_id)
        for message in run_turn(self._model, system, history, text.strip(), self._ctx(pet_id)):
            self._store.append_message(self._key(pet_id), message)
        return self.conversation(pet_id)

    def confirm(self, proposal_id: str) -> dict:
        """AG-4: the only path that sends anything to the clinic."""
        proposal = self._pending(proposal_id)
        payload = proposal.payload
        if proposal.kind == "booking_request":
            detail = f"{payload['reason']} · {payload['preferred_time']}"
        elif proposal.kind == "estimate_reply":
            detail = payload["detail"]
        else:
            detail = payload["note"]
        action, title, after = CONFIRMED[proposal.kind]
        title = title or f"Sent to {self._practice.lead_vet()}"
        self._store.add_clinic_request(payload["pet_id"], proposal.kind, detail)
        self._store.set_proposal_status(proposal_id, "confirmed")
        key = self._key(payload["pet_id"])
        self._store.append_message(key, {"role": "user", "text": action})
        done = {"type": "done", "title": title, "detail": f"{detail} · {after}"}
        self._store.append_message(key, {"role": "assistant", "text": "", "cards": [done]})
        return self.conversation(payload["pet_id"])

    def dismiss(self, proposal_id: str) -> dict:
        proposal = self._pending(proposal_id)
        self._store.set_proposal_status(proposal_id, "dismissed")
        return self.conversation(proposal.payload["pet_id"])

    def set_consent(self, pet_id: str, share_log: bool, deidentified_use: bool) -> dict:
        self._store.set_consent(self._owner_id, Consent(share_log, deidentified_use))
        return self.conversation(pet_id)

    def reset(self, pet_id: str) -> dict:
        self._store.clear_conversation(self._key(pet_id), self._owner_id, pet_id)
        return self.conversation(pet_id)

    # Proposals from the dashboard ----------------------------------------------
    def propose_checkup(self, pet_id: str) -> dict:
        """HT-2: only when the home check-ins really have dropped."""
        checkins = [ci.CheckIn(w, s) for w, s in self._store.checkins(pet_id)]
        if not ci.trend(checkins, self._today).dropping:
            raise ProposalError("Check-ins aren't showing a drop; book from Coming up")
        pet = self._practice.pet(pet_id).name
        return self._propose(
            pet_id,
            f"Ask for a check-up for {pet}",
            "propose_booking",
            {
                "reason": f"Check-up: {pet}'s home check-ins have dropped",
                "preferred_time": "next available",
            },
            f"I've drafted a check-up request with {pet}'s recent check-ins in mind.",
        )

    def propose_estimate_reply(
        self, pet_id: str, estimate_id: str, choice: str, optional_lines: list[str], question: str
    ) -> dict:
        """CO-3: accept, ask for a cheaper option, or ask a question."""
        asked = {
            "accept": "Go ahead with the estimate",
            "cheaper": "Ask for a lower-cost option",
            "question": "Ask a question about the estimate",
        }
        if choice not in asked or (choice == "question" and not question.strip()):
            raise ProposalError("Choose accept, cheaper, or type your question")
        args = {
            "estimate_id": estimate_id,
            "choice": choice,
            "optional_lines": optional_lines,
            "question": question,
        }
        return self._propose(
            pet_id,
            asked[choice],
            "propose_estimate_reply",
            args,
            "Here's your reply, ready for the clinic.",
        )

    def propose_from_triage(self, pet_id: str, level: str, symptom: str, duration: str) -> dict:
        """TR-3: 'within 24 hours' asks for tomorrow's first slot; 'watch' sends a note."""
        pet = self._practice.pet(pet_id).name
        if level == "within_24h":
            return self._propose(
                pet_id,
                f"Book a vet for {pet} within 24 hours",
                "propose_booking",
                {
                    "reason": f"{symptom} ({duration.lower()})",
                    "preferred_time": "first appointment tomorrow",
                },
                "I've drafted a request for the first appointment tomorrow. If things get worse "
                "before then, call the clinic.",
            )
        if level == "watch":
            note = (
                f"{pet}: {symptom.lower()}, {duration.lower()}. Eating and bright. "
                "Keeping an eye on it; would like the vet's view."
            )
            return self._propose(
                pet_id,
                f"Send the vet a note about {pet}",
                "propose_vet_note",
                {"note": note},
                "I've drafted a note for the vet to read in the morning.",
            )
        raise ProposalError("For 'call now', please phone the clinic")

    def propose_follow_up(self, pet_id: str, follow_up: str, when: str) -> dict:
        """VR-3: book the follow-up the vet asked for."""
        return self._propose(
            pet_id,
            f"Book: {follow_up.lower()}",
            "propose_booking",
            {"reason": follow_up, "preferred_time": when or "next available"},
            "I've drafted the booking your vet asked for.",
        )

    def propose_visit_question(self, pet_id: str, visit: str, question: str) -> dict:
        """VR-3: a question about the visit goes to the vet as a note."""
        if not question.strip():
            raise ProposalError("Type your question first")
        return self._propose(
            pet_id,
            "Ask the vet about the visit",
            "propose_vet_note",
            {"note": f"About the visit on {visit}: {question.strip()}"},
            "I've drafted your question for the vet.",
        )

    # Internals -----------------------------------------------------------------
    def _propose(
        self, pet_id: str, user_text: str, tool: str, args: dict[str, Any], reply: str
    ) -> dict:
        """Record a dashboard action as a chat turn: the owner's ask, the proposal, our reply."""
        output = run_tool(tool, args, self._ctx(pet_id))
        if output.card is None:
            raise ProposalError(output.result.get("error", "Couldn't prepare that"))
        call_id = f"{tool}_{uuid.uuid4().hex[:8]}"  # model APIs reject repeated tool-call ids
        for message in (
            {"role": "user", "text": user_text},
            {
                "role": "assistant",
                "text": "",
                "tool_calls": [{"id": call_id, "name": tool, "args": args}],
            },
            {
                "role": "tool",
                "tool_call_id": call_id,
                "name": tool,
                "result": output.result,
                "card": output.card,
            },
            {
                "role": "assistant",
                "text": f"{reply} Nothing goes to the clinic until you tap send.",
            },
        ):
            self._store.append_message(self._key(pet_id), message)
        return self.conversation(pet_id)

    def _open(self, pet_id: str) -> None:
        """AG-1: greet and raise the most important care gap, without calling the model."""
        pet = self._practice.pet(pet_id).name
        output = run_tool("list_care_due", {}, self._ctx(pet_id))
        items = output.result["items"]
        if items:
            title, due = items[0]["title"].lower(), items[0]["due_label"].lower()
            line = f"One thing needs attention: {pet}'s {title} is {due}."
        else:
            line = f"Nothing is due for {pet} right now."
        greeting = (
            f"Hi {self._first_name()}. I'm {pet}'s care assistant from "
            f"{self._practice.clinic_name()}. I can check what's due, explain estimates, "
            "request bookings and pass questions to the vet."
        )
        for message in (
            {
                "role": "assistant",
                "text": greeting,
                "tool_calls": [{"id": "open_care_due", "name": "list_care_due", "args": {}}],
            },
            {
                "role": "tool",
                "tool_call_id": "open_care_due",
                "name": "list_care_due",
                "result": output.result,
                "card": output.card,
            },
            {"role": "assistant", "text": line},
        ):
            self._store.append_message(self._key(pet_id), message)

    def _key(self, pet_id: str) -> str:
        """Each pet has its own conversation, so the assistant never mixes them up."""
        return f"{self._owner_id}:{pet_id}"

    def _ctx(self, pet_id: str) -> ToolContext:
        return ToolContext(self._owner_id, pet_id, self._practice, self._store, self._today)

    def _pending(self, proposal_id: str):
        proposal = self._store.proposal(proposal_id)
        if proposal is None or proposal.owner_id != self._owner_id:
            raise ProposalError("Proposal not found")
        if proposal.status != "pending":
            raise ProposalError(f"Proposal already {proposal.status}")
        return proposal

    def _status(self, proposal_id: str) -> str:
        proposal = self._store.proposal(proposal_id)
        return proposal.status if proposal else "missing"

    def _first_name(self) -> str:
        return self._practice.owner(self._owner_id).name.split(" ")[0]

    def _system(self, pet_id: str) -> str:
        return system_prompt(
            clinic=self._practice.clinic_name(),
            vet=self._practice.lead_vet(),
            pet=self._practice.pet(pet_id).name,
            owner=self._first_name(),
            today=self._today,
        )
