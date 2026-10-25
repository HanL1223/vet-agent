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


class ConsentRequest(BaseModel):
    share_log: bool
    deidentified_use: bool
