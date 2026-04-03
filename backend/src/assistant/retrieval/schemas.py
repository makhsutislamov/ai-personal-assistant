from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class RetrievalFilter(BaseModel):
    source_types: list[str] | None = None
    time_from: datetime | None = None
    time_to: datetime | None = None


class SourceAttribution(BaseModel):
    memory_id: str
    source_type: str
    title: str
    snippet: str
    created_at: datetime


class RetrievalItem(BaseModel):
    memory_id: str
    score: float
    snippet: str
    source: SourceAttribution


class RetrievalResult(BaseModel):
    items: list[RetrievalItem]
    query_latency_ms: float
