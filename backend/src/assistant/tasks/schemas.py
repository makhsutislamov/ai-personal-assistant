from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class TaskIntent(BaseModel):
    objective: str
    due_context: str | None = None
    impact_level: str = "normal"  # "normal" | "high"


class TaskOut(BaseModel):
    task_id: str
    objective: str
    owner: str
    due_at: datetime | None
    status: str
    blocked_reason: str | None
    completion_outcome: str | None
    requires_confirmation: bool = False
    created_at: datetime
    updated_at: datetime
