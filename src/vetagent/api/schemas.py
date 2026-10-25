"""Request bodies. Responses are plain dicts built by the services."""

from pydantic import BaseModel, Field, StrictBool, StrictInt


class ReminderRequest(BaseModel):
    keys: list[str] = Field(min_length=1)


class MessageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


class CheckInRequest(BaseModel):
    scores: dict[str, StrictInt]  # "3" or true are not answers


class TriageRequest(BaseModel):
    symptom: str = Field(min_length=1, max_length=40)
    hours: StrictInt
    eating: StrictBool  # eating and drinking normally
    bright: StrictBool  # bright and alert


class EstimateReply(BaseModel):
    choice: str = Field(pattern="^(accept|cheaper|question)$")
    optional_lines: list[str] = Field(default_factory=list, max_length=20)
    question: str = Field(default="", max_length=1000)


class TickRequest(BaseModel):
    item: str = Field(min_length=1, max_length=80)
    done: StrictBool


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


class SendEstimate(BaseModel):
    explanations: list[str] = Field(max_length=30)  # one per line, in line order


class RecapInstruction(BaseModel):
    text: str = Field(max_length=200)
    days: StrictInt | None = None


class RecapResult(BaseModel):
    name: str = Field(max_length=80)
    status: str
    comment: str = Field(max_length=400)


class RecapDraft(BaseModel):
    pet_id: str = Field(min_length=1, max_length=20)
    visit: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    vet: str = Field(min_length=1, max_length=80)
    summary: str = Field(max_length=1200)
    instructions: list[RecapInstruction] = Field(default_factory=list, max_length=10)
    results: list[RecapResult] = Field(default_factory=list, max_length=10)
    follow_up: str = Field(default="", max_length=120)
    follow_up_by: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class ConsentRequest(BaseModel):
    share_log: bool
    deidentified_use: bool
