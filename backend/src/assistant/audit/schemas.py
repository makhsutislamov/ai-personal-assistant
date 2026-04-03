from __future__ import annotations

from pydantic import BaseModel
from datetime import datetime


class AuditEventOut(BaseModel):
    event_id: str
    actor: str
    action_type: str
    target_type: str
    target_id: str
    before_hash: str | None
    after_hash: str
    created_at: datetime


class AuditQuery(BaseModel):
    actor: str | None = None
    action_type: str | None = None
    target_type: str | None = None
    target_id: str | None = None
    time_from: datetime | None = None
    time_to: datetime | None = None
