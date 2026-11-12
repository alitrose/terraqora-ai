from datetime import datetime
from typing import Literal
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.auth import SupportedLanguage

ChatLanguageChoice = Literal["en", "ta", "ml", "hi", "te", "auto"]
ChatMessageRole = Literal["user", "assistant", "system"]


class ChatSessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=160)
    language: SupportedLanguage = "en"
    farm_id: uuid.UUID | None = None

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("Session title cannot be blank.")
        return cleaned


class ChatSessionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=160)
    language: SupportedLanguage | None = None
    farm_id: uuid.UUID | None = None

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("Session title cannot be blank.")
        return cleaned


class ChatSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    language: SupportedLanguage
    farm_id: uuid.UUID | None = None
    message_count: int = 0
    created_at: datetime
    updated_at: datetime


class ChatCitationOut(BaseModel):
    source_title: str
    section: str


class ChatMessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(..., min_length=1, max_length=2000)
    language: ChatLanguageChoice = "auto"
    include_farm_context: bool = True

    @field_validator("content")
    @classmethod
    def clean_content(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Message content cannot be blank.")
        return cleaned


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    role: ChatMessageRole
    content: str
    citations: list[ChatCitationOut] = Field(default_factory=list)
    provider: str | None = None
    model_name: str | None = None
    latency_ms: int | None = None
    detected_language: SupportedLanguage | None = None
    created_at: datetime


class ChatTurnResponse(BaseModel):
    session: ChatSessionOut
    user_message: ChatMessageOut
    assistant_message: ChatMessageOut
    resolved_language: SupportedLanguage
    language_auto_detected: bool = False
    source_mode: Literal["live_api"] = "live_api"
