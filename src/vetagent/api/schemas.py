"""Request bodies. Responses are plain dicts built by the services."""

from pydantic import BaseModel, Field


class ReminderRequest(BaseModel):
    keys: list[str] = Field(min_length=1)


class MessageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


class CheckInRequest(BaseModel):
    scores: dict[str, int]


class DoseRequest(BaseModel):
    product: str = Field(min_length=1, max_length=100)


class ConsentRequest(BaseModel):
    share_log: bool
    deidentified_use: bool
