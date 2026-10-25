"""Owner care-agent use cases: open the chat, take a message, confirm or dismiss proposals."""

from datetime import date

from vetagent.agent.display import to_chat_items
from vetagent.agent.llm import Model
from vetagent.agent.loop import run_turn
from vetagent.agent.prompts import system_prompt
from vetagent.agent.tools import ToolContext, run_tool
from vetagent.integrations.practice import PracticeSystem
from vetagent.store.sqlite import Consent, Store


class ProposalError(Exception):
    pass


class OwnerAgentService:
    def __init__(
        self,
        practice: PracticeSystem,
        store: Store,
        model: Model,
        today: date,
        owner_id: str,
        pet_id: str,
    ) -> None:
        self._practice = practice
        self._store = store
        self._model = model
        self._today = today
        self._owner_id = owner_id
        self._ctx = ToolContext(owner_id, pet_id, practice, store, today)

    # Queries -----------------------------------------------------------------
    def conversation(self) -> dict:
        if not self._store.messages(self._owner_id):
            self._open()
        pet = self._practice.pet(self._ctx.pet_id)
        consent = self._store.consent(self._owner_id)
        return {
            "clinic": self._practice.clinic_name(),
            "pet": {"name": pet.name, "breed": pet.breed, "age": pet.age_on(self._today)},
            "owner": self._first_name(),
            "model": self._model.name,
            "consent": {
                "share_log": consent.share_log,
                "deidentified_use": consent.deidentified_use,
            },
            "items": to_chat_items(self._store.messages(self._owner_id), self._proposal_status),
        }

    # Commands ------------------------------------------------------------------
    def send(self, text: str) -> dict:
        history = self._store.messages(self._owner_id)
        for message in run_turn(self._model, self._system(), history, text.strip(), self._ctx):
            self._store.append_message(self._owner_id, message)
        return self.conversation()

    def confirm(self, proposal_id: str) -> dict:
        """AG-4: the only path that sends anything to the clinic."""
        proposal = self._pending(proposal_id)
        payload = proposal.payload
        if proposal.kind == "booking_request":
            detail = f"{payload['reason']} · {payload['preferred_time']}"
            done = ("Booking requested", f"{detail} · the clinic will confirm by SMS")
        else:
            detail = payload["note"]
            done = (f"Sent to {self._practice.lead_vet()}", "The team will reply in this chat")
        self._store.add_clinic_request(payload["pet_id"], proposal.kind, detail)
        self._store.set_proposal_status(proposal_id, "confirmed")
        action = "Send to clinic" if proposal.kind == "booking_request" else "Send the note"
        self._store.append_message(self._owner_id, {"role": "user", "text": action})
        self._store.append_message(
            self._owner_id,
            {
                "role": "assistant",
                "text": "",
                "cards": [{"type": "done", "title": done[0], "detail": done[1]}],
            },
        )
        return self.conversation()

    def dismiss(self, proposal_id: str) -> dict:
        self._pending(proposal_id)
        self._store.set_proposal_status(proposal_id, "dismissed")
        return self.conversation()

    def set_consent(self, share_log: bool, deidentified_use: bool) -> dict:
        self._store.set_consent(self._owner_id, Consent(share_log, deidentified_use))
        return self.conversation()

    def reset(self) -> dict:
        self._store.clear_conversation(self._owner_id)
        return self.conversation()

    # Internals -----------------------------------------------------------------
    def _open(self) -> None:
        """AG-1: greet and raise the most important care gap, without calling the model."""
        pet = self._practice.pet(self._ctx.pet_id).name
        output = run_tool("list_care_due", {}, self._ctx)
        items = output.result["items"]
        if items:
            title, due = items[0]["title"].lower(), items[0]["due_label"].lower()
            line = f"One thing needs attention: {pet}'s {title} is {due}."
        else:
            line = f"Nothing is due for {pet} right now."
        greeting = (
            f"Hi {self._first_name()}. I'm {pet}'s care assistant from "
            f"{self._practice.clinic_name()}. I can check what's due, request bookings, "
            "track the care plan and keep the health log."
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
            self._store.append_message(self._owner_id, message)

    def _pending(self, proposal_id: str):
        proposal = self._store.proposal(proposal_id)
        if proposal is None or proposal.owner_id != self._owner_id:
            raise ProposalError("Proposal not found")
        if proposal.status != "pending":
            raise ProposalError(f"Proposal already {proposal.status}")
        return proposal

    def _proposal_status(self, proposal_id: str) -> str:
        proposal = self._store.proposal(proposal_id)
        return proposal.status if proposal else "missing"

    def _first_name(self) -> str:
        pet = self._practice.pet(self._ctx.pet_id)
        return self._practice.owner(pet.owner_id).name.split(" ")[0]

    def _system(self) -> str:
        return system_prompt(
            clinic=self._practice.clinic_name(),
            vet=self._practice.lead_vet(),
            pet=self._practice.pet(self._ctx.pet_id).name,
            owner=self._first_name(),
            today=self._today,
        )
