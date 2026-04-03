from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str


class SourceAttribution(BaseModel):
    memory_id: str
    source_type: str
    title: str
    snippet: str
    created_at: datetime


class ChatResponse(BaseModel):
    response: str
    sources: list[SourceAttribution]
    session_id: str
    model_used: str
    grounded: bool
