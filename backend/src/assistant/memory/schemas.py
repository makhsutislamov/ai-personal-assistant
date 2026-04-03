from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MemoryCandidateIn(BaseModel):
    content: str
    source_type: str
    source_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    sensitivity_class: str = "none"


class MemoryCandidateOut(BaseModel):
    candidate_id: str
    content: str
    source_type: str
    source_ref: str | None
    sensitivity_class: str
    created_at: datetime


class MemoryRecordOut(BaseModel):
    memory_id: str
    source_type: str
    source_ref: str | None
    canonical_text: str
    sensitivity_class: str
    confidence: float
    created_at: datetime


class DeleteFilter(BaseModel):
    memory_id: str | None = None
    source_type: str | None = None
    time_before: datetime | None = None


class DeleteResult(BaseModel):
    deleted_count: int


class DuplicateResult(BaseModel):
    is_duplicate: bool
    existing_memory_id: str | None = None
    similarity_score: float = 0.0
